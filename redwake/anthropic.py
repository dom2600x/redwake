"""Direct Anthropic Messages API with stateless, correlated client tools."""
import os

from .anthropic_usage import API_VERSION
from .providers import TOOLS, ProviderError, http_failure, provider_failure
from .transport import request_json
from .usage import normalize


def response_input(messages):
    system, turns, pending = [], [], []
    for message in messages:
        role = message.get('role')
        if role == 'system':
            if turns or pending: raise ProviderError('response_protocol')
            system.append(message['content'])
        elif role == 'assistant':
            if pending: raise ProviderError('response_protocol')
            if message.get('anthropic_incomplete'):
                turns.append(dict(role='user', content='The previous response was incomplete. No tool calls from it were executed. Continue the investigation.'))
                continue
            content = message['anthropic_content']
            turns.append(dict(role='assistant', content=content))
            pending = [item for item in content if item['type'] == 'tool_use']
        elif role == 'tool':
            if not pending or pending[0]['name'] != message.get('tool_name'):
                raise ProviderError('response_protocol')
            call = pending.pop(0)
            result = dict(type='tool_result', tool_use_id=call['id'], content=message['content'])
            if turns and turns[-1]['role'] == 'user' and isinstance(turns[-1]['content'], list):
                turns[-1]['content'].append(result)
            else:
                turns.append(dict(role='user', content=[result]))
        elif role == 'user':
            if pending: raise ProviderError('response_protocol')
            turns.append(dict(role='user', content=message['content']))
        else:
            raise ProviderError('response_protocol')
    if pending: raise ProviderError('response_protocol')
    return '\n\n'.join(system), turns


def output_items(content):
    if not isinstance(content, list): raise ValueError('Invalid Anthropic content')
    clean, calls, texts, seen = [], [], [], set()
    for item in content:
        if not isinstance(item, dict): raise ValueError('Invalid content block')
        if item.get('type') == 'text':
            if not isinstance(item.get('text'), str): raise ValueError('Invalid text')
            clean.append(dict(type='text', text=item['text']))
            texts.append(item['text'])
        elif item.get('type') == 'tool_use':
            if not all(isinstance(item.get(key), str) and item[key] for key in ('id', 'name')) or 'input' not in item:
                raise ValueError('Invalid tool use')
            if item['id'] in seen: raise ValueError('Duplicate tool ID')
            seen.add(item['id'])
            clean.append({key: item[key] for key in ('type', 'id', 'name', 'input')})
            calls.append(dict(id=item['id'], function=dict(name=item['name'], arguments=item['input'])))
        else:
            # Extended thinking and provider-hosted tools are not requested or supported.
            raise ValueError('Unsupported content block')
    return dict(role='assistant', content='\n'.join(texts), tool_calls=calls, anthropic_content=clean)


class Anthropic:
    def __init__(self, model, endpoint='https://api.anthropic.com', tools=None):
        if endpoint != 'https://api.anthropic.com': raise ValueError('Use the direct Anthropic endpoint')
        if not isinstance(model, str) or not model.strip(): raise ValueError('Choose an Anthropic model explicitly')
        self.key = os.environ.get('ANTHROPIC_API_KEY')
        if not self.key: raise ValueError('Set ANTHROPIC_API_KEY to use Anthropic')
        self.model, self.endpoint = model, endpoint
        self.tools = TOOLS if tools is None else tools

    def chat(self, messages, output_limit, timeout):
        system, turns = response_input(messages)
        tools = [dict(name=tool['function']['name'], description=tool['function']['description'],
                      input_schema=tool['function']['parameters']) for tool in self.tools]
        payload = dict(model=self.model, system=system, messages=turns, tools=tools,
                       stream=False, max_tokens=output_limit)
        try:
            status, response = request_json(self.endpoint + '/v1/messages',
                {'Content-Type': 'application/json', 'x-api-key': self.key, 'anthropic-version': API_VERSION},
                payload, timeout=timeout, limit=1048576, strict_json=True, use_env_proxy=True)
        except Exception as exc:
            raise provider_failure(exc) from None
        if status != 200: raise http_failure(status)
        if not isinstance(response, dict): raise ProviderError('response_protocol', status)
        usage = normalize('anthropic', response)
        result = dict(model=usage['model'], provider_usage=usage,
                      prompt_eval_count=usage['input_tokens'], eval_count=usage['output_tokens'],
                      message=dict(role='assistant', content='', tool_calls=[]))
        if response.get('error') is not None or response.get('stop_reason') == 'refusal':
            result['provider_failure_category'] = 'inference_error'
        elif response.get('type') != 'message' or response.get('role') != 'assistant':
            result['provider_failure_category'] = 'response_protocol'
        else:
            try: result['message'] = output_items(response.get('content'))
            except (ValueError, TypeError, KeyError): result['provider_failure_category'] = 'response_protocol'
            stop = response.get('stop_reason')
            if stop in ('max_tokens', 'pause_turn'):
                result['provider_failure_category'] = 'inference_incomplete'
                result['message']['anthropic_incomplete'] = True
            elif stop not in ('end_turn', 'tool_use'):
                result['provider_failure_category'] = 'response_protocol'
            elif not response.get('content'):
                result['provider_failure_category'] = 'response_protocol'
            elif 'provider_failure_category' not in result and (stop == 'tool_use') != bool(result['message']['tool_calls']):
                result['provider_failure_category'] = 'response_protocol'
        return result
