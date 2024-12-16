import base64
import json
import re

from openai import OpenAI
from tqdm import tqdm

SystemPrompt_test = '''
Please tell me how many pictures you have seen?'''

SystemPrompt_step1 = '''You are a detailed image analyst. Please provide a thorough description of the image. If the image contains only text, present the text in Markdown format. 
If there are visual elements beyond text, describe the image comprehensively, paying special attention to intricate details. 
The goal is to enable someone who has never seen the image to visualize and recreate it based on your description.'''
SystemPrompt_step1_des = '''You are a technical image descriptor. For the given image:

1. If it contains only text, present the exact text in markdown format
2. If it contains visual elements:
- Describe the main technical content
- Include specific measurements, numbers, and text
- State the relationships between visual elements
- Focus on technical details over visual style

Your description should be detailed enough for an AI model to understand the technical content without seeing the image.'''

SystemPrompt_step2 = '''You are a comprehensive issue analyst. The user will provide you with an issue that consists of multiple images and related text. Please connect the content of the text to provide a detailed description for each image, specifically relating it to the issue at hand. Additionally, analyze the role of each image within the context of the issue, explaining its significance and how it complements the overall narrative.

Please analyze each image and provide your analysis in the following structured JSON format:
{
  "image_analyses": [
    {
      "image_id": "<sequential number of the image>",
      "description": "<detailed description of the image in relation to the issue>",
      "analysis": "<analysis of the image's role in the issue>"
    }
  ]
}
'''
SystemPrompt_step2_other = '''You are a detail-oriented issue analyzer focusing on image description. When provided with an issue containing images and text, your task is to:

1. Carefully read through the entire issue to understand its context
2. Create comprehensive descriptions of each image that:
   - Capture all visible elements, features and characteristics shown in the image
   - Explain what the image is demonstrating in relation to the issue
   - Include any relevant technical details shown in the image
   - Describe the image in a way that could help someone understand the issue without seeing the actual image

Please provide your descriptions in the following JSON format:
{
  "images": [
    {
      "image_id": "<sequential number>",
      "context": "<brief context of where this image appears in the issue>", 
      "description": "<detailed description that fully captures what the image shows>",
      "technical_details": "<any specific technical information visible in the image that's relevant to the issue>"
    }
  ]
}

IMPORTANT CHECKS:
- Have you counted all images in the issue?
- Have you described every single image you counted?
- Does the number of descriptions match your total image count?

Focus on creating descriptions that could serve as complete replacements for the original images while maintaining all crucial information needed to understand the issue.
'''

SystemPrompt_step2_des = '''You are a technical image descriptor for software issues. Your task is to create detailed descriptions of ALL images in the issue that will help other AI models understand the issue without seeing the actual images.

For EACH image in the issue:
1. Read and understand the entire issue context including:
- Bug description
- Code samples
- Error messages
- Expected behavior
- Actual results

2. Create a comprehensive description that:
- Details exactly what is shown in the image
- Connects the image content to the issue context
- Includes any visible technical information that's crucial for understanding the issue
- Provides enough detail that an AI model could understand the issue's visual aspects without seeing the image

Please provide your descriptions in this specific JSON format:
{
  "images": [
    {
      "image_id": "<sequential number>",
      "description": "<detailed technical description that fully captures the image content and its relationship to the issue>"
    }
  ]
}

CRITICAL: Ensure you describe EVERY image present in the issue - missing any image would make the issue harder to understand for AI models that cannot see the images.
'''

SystemPrompt_step2_analysis = '''You are a technical image analyst for software issues. Your task is to analyze how each image contributes to understanding and resolving the issue. For each image:

1. Consider:
- How does this image help explain the problem?
- What technical evidence does it provide?
- How does it relate to the issue's context?
- What insights can be drawn from it?

2. Analyze its role in:
- Problem demonstration
- Error verification
- Expected behavior illustration
- Solution hints

Provide your analysis in this JSON format:
{
  "images": [
    {
      "image_id": "<sequential number>",
      "analysis": "<detailed analysis of how this image helps understand and solve the issue>"
    }
  ]
}
'''
SystemPrompt_step2_analysisv2 = '''
You are a specialized technical image analyst for software issues. Your task is to analyze how each image connects to and supports the reported issue. Focus on providing a comprehensive analysis that explains the image's role and value in the issue context.

For each image, analyze:

1. Direct Issue Connection
    - How does this image specifically demonstrate or relate to the reported issue?
    - What aspects of the issue does this image capture or verify?
    - Why was including this image necessary for documenting this issue?

2. Technical Value
    - What key technical details does this image reveal about the issue?
    - How do specific elements in the image help understand the problem?
    - What insights does this image provide for troubleshooting or resolution?

3. Documentation Importance
    - What unique information does this image convey that text alone couldn't?
    - How does this image strengthen the overall issue documentation?
    - What critical details should developers focus on when reviewing this image?

Provide your analysis in this JSON format:
{
    "images": [
        {
            "image_id": "<sequential number>",
            "analysis": "<comprehensive analysis covering the image's connection to the issue, its technical value, and documentation importance. Focus on explaining why this image matters for understanding and resolving the specific issue at hand. Include relevant technical details and their significance to the issue context.>"
        }
    ]
}

Key Guidelines:
- Create a narrative that clearly connects the image to the issue context
- Focus on why this image is necessary for understanding the specific issue
- Include relevant technical details and their significance
- Explain how the image contributes to issue documentation and resolution
- Be thorough but concise in your analysis
'''

SystemPrompt_step3 = '''You are an issue organizer and analyzer. The user will provide you with an issue along with supplementary information that includes descriptions and analyses of images in the issue. Based on the issue and the supplementary information, please think through the details step by step and output the original issue in a structured JSON format. A suggested structure could include:

```json
{
  "problemSummary": "<summary of the problem>",
  "stepsToReproduce": "<steps to reproduce the issue (if applicable)>",
  "expectedResults": "<expected results (if applicable)>",
  "actualResults": "<actual results (if applicable)>"
}
```

Please keep in mind the following:
1. Your structure does not need to match the suggested format exactly. Feel free to add any additional fields that you believe will help clarify the issue, ensuring that it remains clear and structured for better understanding.'''
SystemPrompt_step3_v2 = '''You are an issue organizer and analyzer. The user will provide you with an issue that includes text descriptions and images. Your task is to analyze this information thoroughly and output a structured summary of the issue in JSON format.

The output should include relevant elements as applicable, but you are not required to fill in every field if the information is not available or cannot be accurately summarized. Aim to include:

```json
{
    "problemSummary": "<a concise summary of the problem>",
    "context": "<any relevant background information>",
    "stepsToReproduce": [
        "<step 1: describe the action taken>",
        "<step 2: describe the next action>",
        "...<more steps as necessary>"
    ],
    "expectedResults": "<what the user expected to happen>",
    "actualResults": "<what actually happened>",
    "supplementaryImages": [
        "<descriptions of the images provided>"
    ],
    "additionalNotes": "<any other relevant information or notes>"
}
```

Feel free to omit any fields that are not applicable or where information is uncertain, while ensuring the output remains clear and informative to assist other models in understanding and resolving the issue effectively.
'''
SystemPrompt_step3_COT = '''You are an issue organizer and analyzer. User will provide you with an issue along with supplementary information that includes descriptions and analyses of images in the issue. Based on the issue and the supplementary information, please think through the details step by step and first output your rationale for the structured format, followed by the structured output itself.

The expected response format is as follows:
Rationale: <rationale>
Structured format: {
  "problemSummary": "<summary of the problem>",
  "stepsToReproduce": "<steps to reproduce the issue (if applicable)>",
  "expectedResults": "<expected results (if applicable)>",
  "actualResults": "<actual results (if applicable)>"
}

Please keep in mind the following:
1. The supplementary information may contain errors and is only for reference. You should prioritize the original issue.
2. The output structured format does not need to match the suggested format exactly. You are encouraged to add any additional fields or modify the structure as you see fit to clarify the issue, ensuring that it remains clear and structured for better understanding.

Please note that we not only need structured data, but more importantly, we need the rationale behind it to understand the reasoning process.'''


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def system_message(text):
    message = {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": text
            }
        ]
    }
    return message


def user_message_step1(image_path):
    cur_image = encode_image(image_path)
    message = {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{cur_image}"
                }
            }
        ]
    }
    return message


def user_message_step2(problem_list, image_list):
    contents = []
    for i in range(len(image_list)):
        if image_list[i] == 0:
            contents.append({
                "type": "text",
                "text": problem_list[i]
            })
        elif image_list[i] == 1:
            cur_image = encode_image(problem_list[i])
            contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{cur_image}"
                }
            })
        else:
            pass
    message = {
        "role": "user",
        "content": contents
    }
    return message


def user_message_step3(problem_list, image_list):
    contents = []
    for i in range(len(image_list)):
        if image_list[i] == 0:
            contents.append({
                "type": "text",
                "text": problem_list[i]
            })
        elif image_list[i] == 1:
            cur_image = encode_image(problem_list[i])
            contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{cur_image}"
                }
            })
        else:
            pass
    #    supplementary_info = '''supplementary information:
    #    The following is a description and analysis of the images that appear in the issue. "raw description" refers to the direct description of the image, "description" refers to the description of the image in the context of the issue, and "analysis" refers to the analysis of the image.'''
    #    for description in description_list:
    #        supplementary_info += "\n"
    #        supplementary_info += description

    #    contents.append({
    #        "type": "text",
    #        "text": supplementary_info
    #    })

    message = {
        "role": "user",
        "content": contents
    }
    return message


client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="token-abc123",  # 随便填写，只是为了通过接口参数校验
)


def filter_data(data_list, str_list):
    save_data = []
    for data in data_list:
        if data["instance_id"] in str_list:
            save_data.append(data)
    return save_data


def step1(data_file):
    with open(data_file, "r") as f:
        data_list = json.load(f)
    save_data_list = []
    for data in tqdm(data_list):
        raw_description_list = []
        instance_id = data["instance_id"]
        index = 0
        for problem in data["problem_statement"]:
            if problem.startswith('http'):
                message1 = system_message(SystemPrompt_step1_des)
                message2 = user_message_step1(f"images/{instance_id}/图片{index}.png")
                completion = client.chat.completions.create(
                    model="/gemini/platform/public/llm/huggingface/Qwen/Qwen2-VL-2B-Instruct",
                    messages=[message1, message2],
                    temperature=0.2,
                    seed=42
                )
                index += 1
                raw_description_list.append(completion.choices[0].message.content)
            else:
                continue
        save_data_list.append({
            "instance_id": instance_id,
            "raw_description_list": raw_description_list
        })
    with open("output_qwen2vl2b/step1.json", 'w', encoding='utf-8') as outfile:
        json.dump(save_data_list, outfile, ensure_ascii=False, indent=4)


def step2(data_file, type="des"):
    with open(data_file, "r") as f:
        data_list = json.load(f)
    save_data_list = []
    for data in tqdm(data_list):
        problem_list = []
        image_list = []
        instance_id = data["instance_id"]
        index = 0
        for problem in data["problem_statement"]:
            if problem.startswith('http'):
                problem_list.append(f"images/{instance_id}/图片{index}.png")
                image_list.append(1)
                index += 1
            else:
                problem_list.append(problem)
                image_list.append(0)
        message1 = system_message(SystemPrompt_step2_des)
        if type == "analysis":
            message1 = system_message(SystemPrompt_step2_analysisv2)
        message2 = user_message_step2(problem_list, image_list)
        completion = client.chat.completions.create(
            model="/gemini/platform/public/llm/huggingface/Qwen/Qwen2-VL-2B-Instruct",
            messages=[message1, message2],
            temperature=0.3,
            seed=42
        )
        input_str = completion.choices[0].message.content
        # print(instance_id,f"success,input_str=" + input_str)
        try:
            # 使用正则表达式匹配 JSON 结构
            json_matches = re.findall(r'\{[^{}]*\}', input_str)
            # 将提取到的 JSON 字符串转换为 Python 字典，并存入列表
            description_list = [json.loads(json_str) for json_str in json_matches]
            save_data_list.append({
                "instance_id": instance_id,
                "description_list": description_list
            })
        except json.decoder.JSONDecodeError as e:
            # 如果解析失败，捕获JSONDecodeError异常并处理
            print(instance_id, f"error,input_str=" + input_str)
            # 你可以选择在这里记录错误、跳过当前字符串或采取其他措施
    if type == "des":
        with open(f"output_qwen2vl2b/step2_des.json", 'w', encoding='utf-8') as outfile:
            json.dump(save_data_list, outfile, ensure_ascii=False, indent=4)
    if type == "analysis":
        with open(f"output_qwen2vl2b/step2_analysis.json", 'w', encoding='utf-8') as outfile:
            json.dump(save_data_list, outfile, ensure_ascii=False, indent=4)


def step3(data_file):
    with open(data_file, "r") as f:
        data_list = json.load(f)
    save_data_list = []
    for data in tqdm(data_list):
        problem_list = []
        image_list = []
        instance_id = data["instance_id"]
        index = 0
        for problem in data["problem_statement"]:
            if problem.startswith('http'):
                problem_list.append(f"images/{instance_id}/图片{index}.png")
                image_list.append(1)
                index += 1
            else:
                problem_list.append(problem)
                image_list.append(0)

        message1 = system_message(SystemPrompt_step3_v2)
        message2 = user_message_step3(problem_list, image_list)
        # print(message2)
        completion = client.chat.completions.create(
            model="/gemini/platform/public/llm/huggingface/Qwen/Qwen2-VL-2B-Instruct",
            messages=[message1, message2],
            #temperature = 0.3,
            # seed = 42
        )

        input_str = completion.choices[0].message.content
        # print(instance_id, "success,inputstr=" + input_str)
        try:
            structure_problem = json.loads(input_str.strip().split('\n', 1)[1].rsplit('```', 1)[0].strip())
            save_data_list.append({
                "instance_id": instance_id,
                "structure_problem": structure_problem
            })
        except:
            print(instance_id, "error,input_str=" + input_str)
    with open("output_qwen2vl2b/step3.json", 'w', encoding='utf-8') as outfile:
        json.dump(save_data_list, outfile, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    step1('multi_data_onlyimage.json')
    step2('multi_data_onlyimage.json', "des")
    step2('multi_data_onlyimage.json', "analysis")
    step3('multi_data_onlyimage.json')
