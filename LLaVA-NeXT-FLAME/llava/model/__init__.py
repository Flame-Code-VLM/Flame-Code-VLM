import os

AVAILABLE_MODELS = {
    "llava_llama": "LlavaLlamaForCausalLM, LlavaConfig",
    "llava_qwen": "LlavaQwenForCausalLM, LlavaQwenConfig",
    "llava_mistral": "LlavaMistralForCausalLM, LlavaMistralConfig",
    "llava_mixtral": "LlavaMixtralForCausalLM, LlavaMixtralConfig",
    "flame_deepseek": "FlameDeepseekForCausalLM, FlameConfig",
    # "llava_qwen_moe": "LlavaQwenMoeForCausalLM, LlavaQwenMoeConfig",    
    # Add other models as needed
}

# for model_name, model_classes in AVAILABLE_MODELS.items():
#     try:
#         exec(f"from .language_model.{model_name} import {model_classes}")
#     except Exception as e:
#         print(f"Failed to import {model_name} from llava.language_model.{model_name}. Error: {e}")

for model_name, model_classes in AVAILABLE_MODELS.items():
    try:
        print(f"Attempting to import {model_name}")
        exec(f"from .language_model.{model_name} import {model_classes}")
        print(f"Successfully imported {model_name}")
    except Exception as e:
        print(f"Failed to import {model_name} from llava.language_model.{model_name}. Error: {e}")

print("Finished importing models in __init__.py")