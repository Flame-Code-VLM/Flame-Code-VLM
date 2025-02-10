import re


def postprocess_code_reponse(content):
    if not content:
        return None

    # if there is </s> in the end of the content, remove it
    content = content.rstrip('</s>')

    pattern = r"```(.*?)\n(.*?)```"
    matches = re.findall(pattern, content, re.DOTALL)

    if matches:
        # Extract the code from each match
        return matches[0][1]
    pattern2 = r"'''(.*?)\n(.*?)'''"
    matches2 = re.findall(pattern2, content, re.DOTALL)
    if matches2:
        # Extract the code from each match
        return matches2[0][1]

    # remove \n at the end first
    content = content.strip()
    if content.startswith('```'):
        content = content[3:]
    if content.startswith("'''"):
        content = content[3:]
    # check whether there is ``` in the end
    if content.endswith('```'):
        content = content[:-3]
    if content.endswith("'''"):
        content = content[:-3]

    # remove the single line at the beginning if it is a language label
    if content.startswith('javascript\n'):
        content = content[11:]
    elif content.startswith('typescript\n'):
        content = content[11:]
    elif content.startswith('css\n'):
        content = content[4:]
    elif content.startswith('scss\n'):
        content = content[5:]
    elif content.startswith('sass\n'):
        content = content[5:]
    elif content.startswith('less\n'):
        content = content[5:]
    return content


def estimate_token_count(text):
    def is_chinese(s):
        return any('\u4e00' <= char <= '\u9fff' for char in s)

    if not text:
        return 0

    if is_chinese(text): 
        return len(text)
    else:
        tokens = re.findall(r'\b\w+\b|[^\w\s]', text)

        estimated_count = int(len(tokens) * 1.3) 
        return estimated_count


def process_list_prefix(text):
    list_patterns = [
        r'^\s*\d+\.\s+',
        r'^\s*[-*+]\s+',
    ]
    for pattern in list_patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE)
    return text.strip()


def get_combinations(lst, m):
    def combine(lst, m):
        if m == 0:
            return [[]]
        if not lst:
            return []
        head = lst[0]
        tail = lst[1:]
        with_head = [[head] + comb for comb in combine(tail, m-1)]
        without_head = combine(tail, m)
        return with_head + without_head

    if m > len(lst):
        raise ValueError("m should be less than or equal to the length of lst")
    return combine(lst, m)


def replace_ordered_list_with_unordered(markdown_string):
    ordered_list_pattern = r'^\s*\d+\.\s+(.*)$'
    def replace_match(match):
        return f'- {match.group(1)}'
    output_string = re.sub(ordered_list_pattern, replace_match,
                           markdown_string, flags=re.MULTILINE)

    return output_string
