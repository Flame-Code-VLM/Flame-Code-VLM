from typing import NamedTuple, Optional, TypedDict


class ProjectInfo(TypedDict):
    system_purpose: str
    requirements: str
    layout: str
    tech_plan: str
    dev_plan: str
    style: str
    code: str


class ComponentDataParams(NamedTuple):
    raw_css: str
    filtered_css: str
    sub_components_token_num: dict
    raw_component: str
    raw_component_tokens: int
    debug_component: str
    bug_free: bool
    explaination: str
    file_type: str
    code_with_placeholder_img: str
    code_with_ori_img: str
    system_requirement: str
    iter_num: int
    task_idx: int
    total_task_num: int
    task_description: str


class GenCodeParams(NamedTuple):
    iter_num: int
    dev_plan_list: list
    start_code_snippet: str
    system_purpose_inference: str
    requirements: str
    layouts: str
    tech_architecture: str
    dev_plan: str
    project_info: ProjectInfo
    system_purpose_inference_idx: int
    output_path: str
    source_component_name: str
    source_component_data: ComponentDataParams
    code_snippet: Optional[str] = None  


class StageOnePipelineParams(NamedTuple):
    system_purpose_inference_idx: int
    system_purpose_inference: str
    source_component_name: str
    source_component_data: ComponentDataParams
    output_path: str
    code_snippet: Optional[str] = None


class StageNPipelineParams(NamedTuple):
    system_purpose_inference_idx: int
    iter_num: int
    project_info: ProjectInfo
    source_component_name: str
    source_component_data: ComponentDataParams
    output_path: str
    code_snippet: Optional[str] = None


class EvolCodeParams(NamedTuple):
    """
    Parameters for the evol code
    """
    style: str
    code: str
    iter_num: int
    source_component_name: str
    source_component_data: ComponentDataParams
    output_path: str
    infer_num: Optional[int] = 3
    infer_history: Optional[list] = []
