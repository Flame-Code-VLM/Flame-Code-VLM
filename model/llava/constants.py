CONTROLLER_HEART_BEAT_EXPIRATION = 30
WORKER_HEART_BEAT_INTERVAL = 15

LOGDIR = "."

# Model Constants
IGNORE_INDEX = -100
IMAGE_TOKEN_INDEX = -200
DEFAULT_IMAGE_TOKEN = "<image>"
DEFAULT_IMAGE_PATCH_TOKEN = "<im_patch>"
DEFAULT_IM_START_TOKEN = "<im_start>"
DEFAULT_IM_END_TOKEN = "<im_end>"

PROMPT_DICT = { 
    # v0: instruction + image => css + js/ts
    "v0": (
        "Below is a front-end development task with an input image showing the desired result."
        "Create React code to replicate the design in the image, including layout, typography, and styling."
        "Provide two code sections:'// CSS\n[CSS code]\n\n// [Implementation language (JS/TS/JSX/TSX)]\n[Implementation code]'.\n\n"
        "### Instruction:\n{instruction}\n\n### Input Image:\n{image}\n\n### Response:\n"
    ),
    "v0_res": ( 
        "{css_code}\n\n{code}\n\n"
    ),
    # v1: instruction + layout desc + image   ==> css + js/ts
    "v1": (
        "You'll be provided with an instruction, a layout description, and an input image showing the desired result."
        "Create React code to replicate the design, including layout, typography, and styling."
        "Provide two code sections in this format:'// CSS\n[CSS code]\n\n// [React Implementation (JS/TS/JSX/TSX)]\n[Implementation code]'.\n\n"
        "### Instruction:\n{instruction}\n\n### Layout Description:\n{layout}\n\n### Input Image:\n{image}\n\n### Response:\n"
    ),
    "v1_res": ( 
        "{css_code}\n\n{code}\n\n"
    ),
    # v2: instruction + image ==> layout desc + css + js/ts
    "v2": ( 
        "Below is a front-end development task instruction with an input image showing the desired result."
        "Generate React code to replicate the design in the image, including layout, typography, and styling."
        "Provide your response in three parts:'// Layout Description\n[Describe the component layout]\n\n// CSS\n[CSS/SCSS code]\n\n// [React Implementation (JS/TS/JSX/TSX)]\n[Component code]'.\n\n"
        "### Instruction:\n{instruction}\n\n### Input Image:\n{image}\n\n### Response:\n"

    ),
    "v2_res": ( 
        "// Layout Description\n{layout}\n\n{css_code}\n\n{code}\n\n"
    ),
    # v3: layout desc + image  ==> css + js/ts
    "v3": (
        "Below are a layout description and an input image showing the desired result."
        "Generate React code and styles to replicate the design in the image, including layout, typography, and styling."
        "Provide your response in this format:'// CSS\n[CSS/SCSS code]\n\n// [React Implementation (JS/TS/JSX/TSX)]\n[Component code]'.\n\n"
        "### Layout Description:\n{layout}\n\n### Input Image:\n{image}\n\n### Response:\n"
    ),
    "v3_res": ( 
        "{css_code}\n\n{code}\\"
    ),
    # v4: css + js/ts + image ==> layout desc
    "v4": (
        "Below are a React code snippet with CSS and an image showing its rendering result."
        "Describe the layout of components based on the provided code and image."
        "### Code:\n{css_code}\n\n{code}\n\n### Input Image:\n{image}\n\n### Response:\n"
    ),
    "v4_res": ( 
        "// Layout Description\n{layout}\n\n"
    ),
    # v5: image ==> layout desc + css + js/ts
    "v5": (  
        "Below is an image of the page we want to create."
        "Generate React code to replicate the design, including layout, typography, and styling. Also provide a layout description."
        "Format your response as follows:'// Layout Description\n[Describe component layout]\n\n// CSS\n[CSS/SCSS code]\n\n// [React Implementation (JS/TS/JSX/TSX)]\n[Component code]'.\n\n"
        "### Input Image:\n{image}\n\n### Response:\n"
    ),
    "v5_res": ( 
        "// Layout Description\n{layout}\n\n{css_code}\n\n{code}\n\n"
    ),
    # v6: image ==> css + js/ts
    "v6": (
        "Below is an image of the page to create."
        "Generate React code and styles to replicate the design, including layout, typography, and styling."
        "Format your response as follows:'// CSS\n[CSS/SCSS code]\n\n// [React Implementation (JS/TS/JSX/TSX)]\n[Component code]'.\n\n"
        "### Input Image:\n{image}\n\n### Response:\n" 
    ),
    "v6_res": ( 
        "{css_code}\n\n{code}\n\n"
    ), 
    # v7: image ==> layout desc
    "v7": ( 
        "Analyze the provided image of a webpage and describe its layout and components in detail."
        "### Input Image:\n{image}\n\n### Response:\n" 
    ),
    "v7_res": ( 
        "// Layout Description\n{layout}\n\n"
    ),
    # v8: image ==> instruction
    "v8": (
        "Based on the provided input image of a webpage screenshot, infer the task description that would be required to create this image." 
        "### Input Image:\n{image}\n\n### Response:\n" 
    ),
    "v8_res": ( 
        "// Task description\n{layout}\n\n"
    ),
    # v9: image ==> instruction + layout desc
    "v9": (
        "Analyze the provided image of a webpage screenshot. Infer the task description that would be required to create this image, and describe the observed layout of its components" 
        "### Input Image:\n{image}\n\n### Response:\n" 
    ),
    "v9_res": ( 
        "// Task description\n{instruction}// Layout Description\n{layout}\n\n"
    ), 
}