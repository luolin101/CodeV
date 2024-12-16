import base64
import json
import re
from openai import OpenAI
from tqdm import tqdm

SystemPrompt_step1_des = '''You are a technical image descriptor. For the given image:

1. If it contains only text, present the exact text in markdown format
2. If it contains visual elements:
- Describe the main technical content
- Include specific measurements, numbers, and text
- State the relationships between visual elements
- Focus on technical details over visual style

Your description should be detailed enough for an AI model to understand the technical content without seeing the image.'''

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

SystemPrompt_step2_analysis = '''
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

SystemPrompt_step3 = '''You are an issue organizer and analyzer. The user will provide you with an issue that includes text descriptions and images. Your task is to analyze this information thoroughly and output a structured summary of the issue in JSON format.

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
    message = {
        "role": "user",
        "content": contents
    }
    return message


client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="token-abc123",
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
                message2 = user_message_step1(f"images/{instance_id}/Image{index}.png")
                completion = client.chat.completions.create(
                    model="/gemini/platform/public/llm/huggingface/Qwen/Qwen2-VL-2B-Instruct",
                    messages=[message1, message2],
                    temperature=0.2
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
                problem_list.append(f"images/{instance_id}/Image{index}.png")
                image_list.append(1)
                index += 1
            else:
                problem_list.append(problem)
                image_list.append(0)
        message1 = system_message(SystemPrompt_step2_des)
        if type == "analysis":
            message1 = system_message(SystemPrompt_step2_analysis)
        message2 = user_message_step2(problem_list, image_list)
        completion = client.chat.completions.create(
            model="/gemini/platform/public/llm/huggingface/Qwen/Qwen2-VL-2B-Instruct",
            messages=[message1, message2],
            temperature=0.3
        )
        input_str = completion.choices[0].message.content
        try:
            json_matches = re.findall(r'\{[^{}]*\}', input_str)
            description_list = [json.loads(json_str) for json_str in json_matches]
            save_data_list.append({
                "instance_id": instance_id,
                "description_list": description_list
            })
        except json.decoder.JSONDecodeError as e:
            print(instance_id, f"error,input_str=" + input_str)
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
                problem_list.append(f"images/{instance_id}/Image{index}.png")
                image_list.append(1)
                index += 1
            else:
                problem_list.append(problem)
                image_list.append(0)

        message1 = system_message(SystemPrompt_step3)
        message2 = user_message_step3(problem_list, image_list)
        completion = client.chat.completions.create(
            model="/gemini/platform/public/llm/huggingface/Qwen/Qwen2-VL-2B-Instruct",
            messages=[message1, message2]
        )

        input_str = completion.choices[0].message.content
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
