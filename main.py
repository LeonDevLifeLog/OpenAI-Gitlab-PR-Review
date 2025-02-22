import os
import requests
from flask import Flask, request
import openai

app = Flask(__name__)
openai.api_key = os.environ.get("OPENAI_API_KEY")
openai.base_url = os.environ.get("OPENAI_API_BASE_URL")
gitlab_token = os.environ.get("GITLAB_TOKEN")
gitlab_url = os.environ.get("GITLAB_URL")
model_name = os.environ.get("OPENAI_API_MODEL")

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.json
    if payload.get("object_kind") == "merge_request":
        if payload["object_attributes"] ["action"] != "open":
            return "这不是一个打开的PR", 200
        project_id = payload["project"] ["id"]
        mr_id = payload["object_attributes"] ["iid"]
        changes_url = f"{gitlab_url}/projects/{project_id}/merge_requests/{mr_id}/changes"

        headers = {"Private-Token": gitlab_token}
        response = requests.get(changes_url, headers=headers)
        mr_changes = response.json()

        diffs = [change["diff"] for change in mr_changes["changes"]]

        pre_prompt = "请审查以下git diff代码更改，重点关注结构、安全性和清晰度。"

        questions = """
        问题：
        1. 概述关键更改。
        2. 新增或修改的代码是否清晰？
        3. 注释和命名是否具有描述性？
        4. 是否可以简化复杂性？举例说明。
        5. 存在任何bug？具体位置？
        6. 可能的安全问题？
        7. 对最佳实践的建议？
        """

        messages = [
            {"role": "system", "content": "您是一名资深开发者，正在审查代码更改。"},
            {"role": "user", "content": f"{pre_prompt}\n\n{''.join(diffs)}{questions}"},
            {"role": "assistant", "content": "请以GitLab友好的markdown格式回复。在您的响应中包含每个问题的简洁版本。"},
        ]

        try:
            completions = openai.ChatCompletion.create(
                deployment_id=model_name,
                model=model_name,
                temperature=0.2,
                stream=False,
                messages=messages
            )
            answer = completions.choices[0].message["content"].strip()
            answer += "\n\n此评论由一只人工智能鸭生成。"
        except Exception as e:
            print(e)
            answer = "对不起，我今天感觉不太好。请让人类来审查这个PR。"
            answer += "\n\n此评论由一只人工智能鸭生成。"
            answer += "\n\n错误: " + str(e)

        print(answer)
        comment_url = f"{gitlab_url}/projects/{project_id}/merge_requests/{mr_id}/notes"
        comment_payload = {"body": answer}
        comment_response = requests.post(comment_url, headers=headers, json=comment_payload)
    elif payload.get("object_kind") == "push":
        project_id = payload["project_id"]
        commit_id = payload["after"]
        commit_url = f"{gitlab_url}/projects/{project_id}/repository/commits/{commit_id}/diff"

        headers = {"Private-Token": gitlab_token}
        response = requests.get(commit_url, headers=headers)
        changes = response.json()

        changes_string = ''.join([str(change) for change in changes])

        pre_prompt = "请审查最近提交的git diff，重点关注清晰度、结构和安全性。"

        questions = """
        问题：
        1. 概述更改（Changelog风格）。
        2. 新增或修改的代码是否清晰？
        3. 注释和命名是否合适？
        4. 是否可以在不破坏功能的情况下简化？举例说明。
        5. 存在任何bug？具体位置？
        6. 可能的安全问题？
        """

        messages = [
            {"role": "system", "content": "您是一名资深开发者，正在审查代码更改。"},
            {"role": "user", "content": f"{pre_prompt}\n\n{changes_string}{questions}"},
            {"role": "assistant", "content": "请以GitLab友好的markdown格式回复。在您的响应中包含每个问题的简洁版本。"},
        ]

        print(messages)
        try:
            completions = openai.ChatCompletion.create(
                deployment_id=model_name,
                model=model_name,
                temperature=0.2,
                stream=False,
                messages=messages
            )
            answer = completions.choices[0].message["content"].strip()
            answer += "\n\n供参考，我得到的问题如下：\n"
            for question in questions.split("\n"):
                answer += f"\n{question}"
            answer += "\n\n此评论由一只人工智能鸭生成。"
        except Exception as e:
            print(e)
            answer = "对不起，我今天感觉不太好。请让人类来审查这个代码更改。"
            answer += "\n\n此评论由一只人工智能鸭生成。"
            answer += "\n\n错误: " + str(e)

        print(answer)
        comment_url = f"{gitlab_url}/projects/{project_id}/repository/commits/{commit_id}/comments"
        comment_payload = {"note": answer}
        comment_response = requests.post(comment_url, headers=headers, json=comment_payload)

    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)