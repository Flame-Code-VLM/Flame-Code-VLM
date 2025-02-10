const fs = require('fs');
const axios = require('axios');
const OpenAI = require('openai');
require('dotenv').config();

const RETRY_SLEEP_TIME = 20;
const MAX_RETRY_NUM = 10;

class LLMChat {
  constructor() {
    this._statistics = {
      total_input_tokens: 0,
      total_output_tokens: 0,
      total_tokens: 0,
      total_requests: 0,
      input_tokens_per_request: 0,
      output_tokens_per_request: 0,
      max_input_tokens_per_request: 0,
      max_output_tokens_per_request: 0,
      min_input_tokens_per_request: 0,
      min_output_tokens_per_request: 0,
      output_len_over_limit: 0,
    }

    this._key = null;
    this._modelName = '';
    this._baseURL = '';
    this._completionUrl = '';
    this._client = null;
  }

  init(keyInfo) {
    console.log(process.env)
    this._key = keyInfo['key']
    this._completionUrl = keyInfo['completion_url']
    this._baseURL = keyInfo['base_url']
    this._modelName = keyInfo['model_name']

    this._client = new OpenAI({
      baseURL: this._baseURL,
      apiKey: this._key
    });

    console.log('Using key: ', this._key);
  }

  statistic(inputTokens, outputTokens) {
    this._statistics.total_input_tokens += inputTokens;
    this._statistics.total_output_tokens += outputTokens;
    if (outputTokens >= 4095) {
      this._statistics.output_len_over_limit += 1;
    }
    this._statistics.total_tokens += inputTokens + outputTokens;
    this._statistics.total_requests += 1;
    this._statistics.input_tokens_per_request = this._statistics.total_input_tokens / this._statistics.total_requests;
    this._statistics.output_tokens_per_request = this._statistics.total_output_tokens / this._statistics.total_requests;
    this._statistics.max_input_tokens_per_request = Math.max(this._statistics.max_input_tokens_per_request, inputTokens);
    this._statistics.max_output_tokens_per_request = Math.max(this._statistics.max_output_tokens_per_request, outputTokens);
    this._statistics.min_input_tokens_per_request = Math.min(this._statistics.min_input_tokens_per_request, inputTokens);
    this._statistics.min_output_tokens_per_request = Math.min(this._statistics.min_output_tokens_per_request, outputTokens);
    console.log('updated Statistics: ', this._statistics)
  }

  printStatistics() {
    console.log('---------------------------------');
    console.log('Total input tokens: ', this._statistics.total_input_tokens);
    console.log('Total output tokens: ', this._statistics.total_output_tokens);
    console.log('Total tokens: ', this._statistics.total_tokens);
    console.log('Total requests: ', this._statistics.total_requests);
    console.log('Input tokens per request: ', this._statistics.input_tokens_per_request);
    console.log('Output tokens per request: ', this._statistics.output_tokens_per_request);
    console.log('Max input tokens per request: ', this._statistics.max_input_tokens_per_request);
    console.log('Max output tokens per request: ', this._statistics.max_output_tokens_per_request);
    console.log('Min input tokens per request: ', this._statistics.min_input_tokens_per_request);
    console.log('Min output tokens per request: ', this._statistics.min_output_tokens_per_request);
    console.log('Output length over limit: ', this._statistics.output_len_over_limit);
    console.log('---------------------------------');
  }


  async chat({ prompt, chatHistory = [], functions = [], maxTokens = 4096, temperature = 0.1 }) {


    // let data = JSON.stringify({
    //   "messages": [...chatHistory, { content: prompt, role: 'user' }],
    //   "model": this._modelName,
    //   // "frequency_penalty": 0,
    //   "max_tokens": maxTokens,
    //   // "presence_penalty": 0,
    //   // "stop": null,
    //   "stream": false,
    //   "temperature": temperature,
    //   // "top_p": 1,
    //   // "logprobs": false,
    //   // "top_logprobs": null
    // });

    // let config = {
    //   method: 'post',
    //   maxBodyLength: Infinity,
    //   url: self._completionUrl,
    //   headers: {
    //     'Content-Type': 'application/json',
    //     'Accept': 'application/json',
    //     'Authorization': 'Bearer ' + this._key
    //   },
    //   data: data
    // };

    const messages = [...chatHistory, { content: prompt, role: 'user' }]

    for (let attempt = 0; attempt < MAX_RETRY_NUM; attempt++) {
      try {
        const response = await this._client.chat.completions.create({
          model: this._modelName,
          messages: messages
        })
        // const response = await axios(config)
        // response.data && response.data.usage && this.statistic(response.data.usage.prompt_tokens, response.data.usage.completion_tokens);
        // this.printStatistics();
        // if (response.status === 200) {
        //   return { content: response.data.choices[0].message.content, error_code: 200 };
        // } else {
        //   throw new Error(response.status);
        // }
        return {
          "content": response.choices[0].message.content,
          "error_code": 200,
        }
      } catch (error) {
        // print error code
        console.log('LLM Error: ', error, error.response.status);
        console.error(`LLM Attempt ${attempt + 1} failed. Exception: `, error.message);
        if (error.message.includes('Failed to buffer the request body')) {
          return { content: null, error_code: 400 }
        }
        if (error.response.status === 400 || error.response.status === 401 || error.response.status === 402 || error.response.status === 422) {
          return { content: null, error_code: error.response.status }
        }
      }
      await new Promise(resolve => setTimeout(resolve, RETRY_SLEEP_TIME * 1000));
    }
    return { content: null, error_code: 403 }
  }
}

const llmChat = new LLMChat();
llmChat.init({
  "key": process.env.LLM_KEY,
  "model_name": process.env.MODEL_NAME,
  "base_url": process.env.LLM_BASE_URL,
  "completion_url": process.env.LLM_COMPLETION_URL,
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
  "is_available": true,
  "error_code": 0
});

// (async () => {
//   const response = await llmChat.chat({
//     prompt: 'Hello, how are you?',
//   });

//   console.log('Chat Response:', response);
// })();

module.exports = {
  llmChat
}
