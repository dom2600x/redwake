"""Direct, stateless OpenAI Responses API adapter; no provider-hosted tools."""
import json
import os

from .providers import TOOLS, ProviderError, http_failure, provider_failure
from .transport import request_json
from .usage import normalize


def response_input(messages):
    items, pending = [], []
    for message in messages:
        role = message.get('role')
        if role == 'assistant':
            if pending: raise ProviderError('response_protocol')
            if message.get('openai_incomplete'):
                items.append(dict(role='user', content='The previous response was incomplete. No tool calls from it were executed. Continue the investigation.'))
                continue
            output = message.get('openai_output', [])
            items.extend(output)
            pending = [item for item in output if item['type'] == 'function_call']
        elif role == 'tool':
            if not pending or pending[0]['name'] != message.get('tool_name'):
                raise ProviderError('response_protocol')
            call = pending.pop(0)
            items.append(dict(type='function_call_output', call_id=call['call_id'], output=message['content']))
        elif role in ('system', 'user'):
            if pending: raise ProviderError('response_protocol')
            items.append(dict(role=role, content=message['content']))
        else:
            raise ProviderError('response_protocol')
    if pending: raise ProviderError('response_protocol')
    return items


def output_items(output):
    """Keep only replayable output fields; never persist response errors or headers."""
    if not isinstance(output, list): raise ValueError('Invalid response output')
    result, calls, texts, seen = [], [], [], set()
    for item in output:
        if not isinstance(item, dict): raise ValueError('Invalid output item')
        kind = item.get('type')
        if kind == 'function_call':
            if not all(isinstance(item.get(key), str) and item[key] for key in ('call_id', 'name', 'arguments')):
                raise ValueError('Invalid function call')
            if item['call_id'] in seen: raise ValueError('Duplicate function call')
            seen.add(item['call_id'])
            clean = {key: item[key] for key in ('type', 'call_id', 'name', 'arguments')}
            try: args = json.loads(item['arguments'])
            except (ValueError, TypeError): args = item['arguments']
            calls.append(dict(id=item['call_id'], function=dict(name=item['name'], arguments=args)))
        elif kind == 'reasoning':
            clean = dict(type='reasoning', summary=[])
            summary = item.get('summary', [])
            if not isinstance(summary, list): raise ValueError('Invalid reasoning summary')
            for part in summary:
                if not isinstance(part, dict) or part.get('type') != 'summary_text' or not isinstance(part.get('text'), str):
                    raise ValueError('Invalid reasoning summary')
                clean['summary'].append(dict(type='summary_text', text=part['text']))
            if 'encrypted_content' in item:
                if not isinstance(item['encrypted_content'], str): raise ValueError('Invalid reasoning content')
                clean['encrypted_content'] = item['encrypted_content']
        elif kind == 'message':
            if item.get('role') != 'assistant' or not isinstance(item.get('content'), list):
                raise ValueError('Invalid assistant message')
            clean = dict(type='message', role='assistant', content=[])
            for part in item['content']:
                if not isinstance(part, dict): raise ValueError('Invalid message content')
                field = {'output_text': 'text', 'refusal': 'refusal'}.get(part.get('type'))
                if field is None or not isinstance(part.get(field), str): raise ValueError('Invalid message content')
                content = dict(type=part['type'], **{field: part[field]})
                if field == 'text': content['annotations'] = []
                clean['content'].append(content)
                texts.append(part[field])
        else:
            raise ValueError('Unsupported output type')
        if 'id' in item:
            if not isinstance(item['id'], str): raise ValueError('Invalid output identifier')
            clean['id'] = item['id']
        result.append(clean)
    return dict(role='assistant', content='\n'.join(texts), tool_calls=calls, openai_output=result)


class OpenAI:
    def __init__(self, model, endpoint='https://api.openai.com', tools=None):
        if endpoint != 'https://api.openai.com': raise ValueError('Use the direct OpenAI endpoint')
        if not isinstance(model, str) or not model.strip(): raise ValueError('Choose an OpenAI model explicitly')
        self.key = os.environ.get('OPENAI_API_KEY')
        if not self.key: raise ValueError('Set OPENAI_API_KEY to use OpenAI')
        self.model, self.endpoint = model, endpoint
        self.tools = TOOLS if tools is None else tools

    def chat(self, messages, output_limit, timeout):
        tools = [dict(type='function', strict=False, **tool['function']) for tool in self.tools]
        payload = dict(model=self.model, input=response_input(messages), tools=tools,
                       store=False, stream=False, max_output_tokens=output_limit,
                       include=['reasoning.encrypted_content'], service_tier='default')
        try:
            status, response = request_json(self.endpoint + '/v1/responses',
                {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key},
                payload, timeout=timeout, limit=1048576, strict_json=True, use_env_proxy=True)
        except Exception as exc:
            raise provider_failure(exc) from None
        if status != 200: raise http_failure(status)
        if not isinstance(response, dict): raise ProviderError('response_protocol', status)
        usage = normalize('openai', response)
        result = dict(model=usage['model'], provider_usage=usage,
                      prompt_eval_count=usage['input_tokens'], eval_count=usage['output_tokens'],
                      message=dict(role='assistant', content='', tool_calls=[]))
        # A failed/incomplete or malformed response can still consume billed tokens.
        # Return allowlisted usage before the runner records a fixed failure category.
        if response.get('error') is not None or response.get('status') == 'failed':
            result['provider_failure_category'] = 'inference_error'
        elif response.get('status') not in ('completed', 'incomplete'):
            result['provider_failure_category'] = 'response_protocol'
        else:
            try: result['message'] = output_items(response.get('output'))
            except (ValueError, TypeError, KeyError): result['provider_failure_category'] = 'response_protocol'
            if response.get('status') == 'incomplete':
                # Never execute partial proposals; retain usage and partial output.
                result['provider_failure_category'] = 'inference_incomplete'
                result['message']['openai_incomplete'] = True
        return result
