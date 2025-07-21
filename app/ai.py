# To run this code you need to install the following dependencies:
# pip install google-genai

import base64
import os
from google import genai
from google.genai import types


def generate(prompt: str) -> str:
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=5000,
        ),
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["articles"],
            properties={
                "articles": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    items=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        required=["title", "summary", "sources"],
                        properties={
                            "title": genai.types.Schema(
                                type=genai.types.Type.STRING,
                            ),
                            "summary": genai.types.Schema(
                                type=genai.types.Type.STRING,
                            ),
                            "sources": genai.types.Schema(
                                type=genai.types.Type.ARRAY,
                                items=genai.types.Schema(
                                    type=genai.types.Type.STRING,
                                ),
                            ),
                        },
                    ),
                ),
            },
        ),
        system_instruction=[
            types.Part.from_text(
                text="""You will be provided with some news that I have collected from rss feeds and have formated them. provide them as a news feed to me. write comprehensive paragraphs on them if you can expand on it. make sure the feed is in english.provide the news in a consistent format and provide resources. the format should be as follows:
                                 use json. each article has 3 fields. title as string, summary as string and sources as array of strings. you should return array of articles """
            ),
        ],
    )

    output = ""

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if chunk.text:
            output += chunk.text
        else:
            pass
    return output
