import asyncio
import aiohttp
import time 

url = "xxxx"
proxy_url = f"http://{url}:8000/generate_text"

final_prompt = """
请你对以下文章内容提取关键实体，实体信息需要包括：
1. 公司或者组织：如果文章中提到了公司、研究所、企业、事业单位等就业部门，请提取出来。
2. 个人：如果文章中提到了个人，请提取出来。
3. 薪资待遇：如果文章中提到了工作岗位的薪资待遇，请提取。

同时，分析这个文章作者写文章的目的是什么：
1. 分享经验
2. 问题咨询

文章如下：
文章标题: xxxxxx
文章正文: xxxxxx

输出格式如：
公司或者组织: xxx,xxx,xxx
个人: xxx,xxx,xxx
薪资待遇: xxx,xxx,xxx
写文章目的: xxx
"""


async def send_request(session):
    request_data = {"input_text": final_prompt, 
         "max_new_tokens": 128,
         "model_max_length": 4096,
         "do_sample": False,
         "temperature": 0.0}
    try:
        async with session.post(proxy_url, json=request_data) as response:
            result = await response.json()
            # print(result)
    except Exception as e:
        print(f"Error sending request: {e}")

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [send_request(session) for _ in range(64)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    for i in range(10000):
        begin_time = time.time()
        asyncio.run(main())
        end_time = time.time()
        print(f"index = {i}, cost time = {end_time - begin_time}")