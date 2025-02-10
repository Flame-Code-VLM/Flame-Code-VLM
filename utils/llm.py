import os
import time
from openai import OpenAI
import re
from dotenv import load_dotenv

load_dotenv()

DS_ERROR_CODES = [{
    'code': 400,
    'message': 'Bad Request'  # skip
}, {
    'code': 401,
    'message': 'Unauthorized'  # terminate
}, {
    'code': 402,
    'message': 'Payment Required'  # terminate
}, {
    'code': 422,
    'message': 'Wrong input'  # skip
}, {
    'code': 429,
    'message': 'Rate limit exceeded'  # retry
}, {
    'code': 500,
    'message': 'Internal Server Error'  # retry
}, {
    'code': 503,
    'message': 'Service Unavailable'  # retry
}, {
    'code': 403,
    'message': 'Forbidden'  # terminate
}]

SUCCESS_CODE = 200
BAD_REQUEST_ERROR = 400
UNAUTHORIZED_ERROR = 401
FORBIDDEN_ERROR = 403
MAX_LENGTH_EXCEEDED_ERROR = 406
INTERNAL_SERVER_ERROR = 500  # retry
BAD_GATEWAY_ERROR = 502
SERVICE_UNAVAILABLE_ERROR = 503
GATEWAT_TIMEOUT_ERROR = 504  # retry
SKIP_ERROR = 998
UNKNOWN_ERROR = 999


def extract_error_code(error_message):
    match = re.search(r'Error code: (\d+)', error_message)

    if match:
        error_code = match.group(1)
        return int(error_code)
    else:
        return UNKNOWN_ERROR


class LLMChat(object):
    def __init__(self):
        # statistics
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_tokens = 0
        self._total_requests = 0
        self._input_tokens_per_request = 0
        self._output_tokens_per_request = 0
        self._max_input_tokens_per_request = 0
        self._max_output_tokens_per_request = 0
        self._min_input_tokens_per_request = 0
        self._min_output_tokens_per_request = 0
        self._output_len_over_limit = 0
        self._key = None
        self._model_name = ''
        self._client = None
        self.errors = set()  # error codes

    def init(self, key_info):
        if key_info:
            self._key = key_info['key']
            self._model_name = key_info['model_name']
            self._base_url = key_info['base_url']
            self._client = OpenAI(api_key=self._key,
                                  base_url=self._base_url)
            self.init_statistics(
                key_info['total_input_tokens'],
                key_info['total_output_tokens'],
                key_info['total_tokens'],
                key_info['total_requests'],
                key_info['input_tokens_per_request'],
                key_info['output_tokens_per_request'],
                key_info['max_input_tokens_per_request'],
                key_info['max_output_tokens_per_request'],
                key_info['min_input_tokens_per_request'],
                key_info['min_output_tokens_per_request'],
                key_info['output_len_over_limit']
            )
            self.errors.clear()
            return True
        else:
            return False

    def init_statistics(self, total_input_tokens, total_output_tokens, total_tokens, total_requests, input_tokens_per_request, output_tokens_per_request, max_input_tokens_per_request, max_output_tokens_per_request, min_input_tokens_per_request, min_output_tokens_per_request, output_len_over_limit):
        self._total_input_tokens = total_input_tokens
        self._total_output_tokens = total_output_tokens
        self._total_tokens = total_tokens
        self._total_requests = total_requests
        self._input_tokens_per_request = input_tokens_per_request
        self._output_tokens_per_request = output_tokens_per_request
        self._max_input_tokens_per_request = max_input_tokens_per_request
        self._max_output_tokens_per_request = max_output_tokens_per_request
        self._min_input_tokens_per_request = min_input_tokens_per_request
        self._min_output_tokens_per_request = min_output_tokens_per_request
        self._output_len_over_limit = output_len_over_limit

    def statistics(self, input_tokens, output_tokens):
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        if output_tokens >= 4095:
            self._output_len_over_limit += 1
        self._total_tokens = self._total_input_tokens + self._total_output_tokens
        self._total_requests += 1
        self._input_tokens_per_request = self._total_input_tokens / self._total_requests
        self._output_tokens_per_request = self._total_output_tokens / self._total_requests
        self._max_input_tokens_per_request = max(
            self._max_input_tokens_per_request, input_tokens)
        self._max_output_tokens_per_request = max(
            self._max_output_tokens_per_request, output_tokens)
        self._min_input_tokens_per_request = min(
            self._min_input_tokens_per_request, input_tokens)
        self._min_output_tokens_per_request = min(
            self._min_output_tokens_per_request, output_tokens)

    def print_statistics(self):
        print('-------------------------------------')
        print("Total input tokens used: ", self._total_input_tokens)
        print("Total output tokens used: ", self._total_output_tokens)
        print("Total tokens used: ", self._total_tokens)
        print("Total requests made: ", self._total_requests)
        print("Output length over limit: ", self._output_len_over_limit)
        print("Average input tokens per request: ",
              self._input_tokens_per_request)
        print("Average output tokens per request: ",
              self._output_tokens_per_request)
        print("Max input tokens used in a request: ",
              self._max_input_tokens_per_request)
        print("Max output tokens used in a request: ",
              self._max_output_tokens_per_request)
        print("Min input tokens used in a request: ",
              self._min_input_tokens_per_request)
        print("Min output tokens used in a request: ",
              self._min_output_tokens_per_request)
        print('-------------------------------------')

    def print_response(self, response):
        if response and response.choices and response.choices[0].message and response.choices[0].message.content:
            print(f'** LLM Response:\n\t{response.choices[0].message.content}')

    def chat(self, prompt, chat_hist=[], temp=0.1):
        messages = chat_hist + [
            {'role': 'user', 'content': prompt}
        ]

        max_retries = 5  # Number of retries
        delay = 20  # Seconds to wait between retries

        for attempt in range(max_retries):
            try:
                response = self._client.chat.completions.create(
                    model=self._model_name,
                    messages=messages,
                    # max_tokens=4096,
                    # frequency_penalty=0.2,
                    temperature=temp,
                    stream=False
                )
                # self.print_response(response)

                self.statistics(response.usage.prompt_tokens,
                                response.usage.completion_tokens)

                # self.print_statistics()

                return {
                    "content": response.choices[0].message.content,
                    "error_code": 200,
                    "output_token_len": response.usage.completion_tokens
                }
            except Exception as e:
                print(f"Attempt {attempt+1} failed: {e}", type(e))
                error_code = extract_error_code(str(e))
                print(
                    f"Attempt {attempt+1} failed: {e}, error code: {error_code}")
                if error_code != INTERNAL_SERVER_ERROR and error_code != GATEWAT_TIMEOUT_ERROR and error_code != MAX_LENGTH_EXCEEDED_ERROR:
                    print('done chatting with http error')
                    return {
                        "content": None,
                        "error_code": error_code,
                        "output_token_len": 0
                    }
                time.sleep(delay)
        return {
            "content": None,
            "error_code": 403,
            "output_token_len": 0
        }


llm_chat = LLMChat()
llm_chat.init({
    "key": os.getenv('LLM_KEY'),
    "model_name": os.getenv('MODEL_NAME'),
    "base_url": os.getenv('LLM_BASE_URL'),
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_tokens": 0,
    "total_requests": 0,
    "input_tokens_per_request": 0,
    "output_tokens_per_request": 0,
    "max_input_tokens_per_request": 0,
    "max_output_tokens_per_request": 0,
    "min_input_tokens_per_request": 0,
    "min_output_tokens_per_request": 0,
    "output_len_over_limit": 54,
    "is_available": True,
    "error_code": 0
})


def chat(prompt, temperature=0.1):
    response = llm_chat.chat(prompt, temp=temperature)
    if response['error_code'] != SUCCESS_CODE:
        if response['error_code'] == MAX_LENGTH_EXCEEDED_ERROR:
            print('TOO LONG, breaking...')
            return None
        print('Error in generating response, breaking...')
        return None

    result = response['content']

    max_continue = 5
    continue_count = 0
    while True:
        if response['output_token_len'] >= 4095:
            chat_hist = [
                {'role': 'user', 'content': prompt},
                {'role': 'assistant', 'content': response['content']}
            ]
            response = llm_chat.chat(
                'continue', chat_hist, temperature)
            print('--- current output len: ', response['output_token_len'])
            if response['error_code'] != SUCCESS_CODE:
                if response['error_code'] == MAX_LENGTH_EXCEEDED_ERROR:
                    print('TOO LONG, breaking...')
                    return result
                print('Error in generating response, breaking...')
                return result
            result += response['content']
            print('--- current result: ', result)
            continue_count += 1
            if continue_count >= max_continue:
                print('--- done generate all')
                break
        else:
            print('--- done generate all')
            break

    return result
