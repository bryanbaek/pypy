from openai import OpenAI
from src.backend.core.config import settings

# Configuration for OpenAI API
client = OpenAI(
    # This is the default and can be omitted
    api_key=settings.OPENAI_API_KEY,
)


def upload_file(file_path: str) -> str:
    with open("file_path.txt", "r") as file:
        file_contents = file.read()

    file_response = client.File.create(file=file_contents, purpose="assistants")

    return file_response.id


def get_gpt_4o_response(prompt: str) -> str:
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4o",
    )

    return response.choices[0].message.content
