import os
import json
from typing import Union, List
from google import genai
from google.genai import types


class GeminiClient:
    def __init__(
        self,
        api_key: str = None,
        model: str = "gemini-2.5-flash",
        system_instruction: Union[str, List[str]] = None,
        response_schema: genai.types.Schema = None,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model
        self.client = genai.Client(api_key=self.api_key)
        self.system_instruction = self._build_system_instruction(system_instruction)
        self.response_schema = response_schema or self._default_schema()

    def _build_system_instruction(
        self, instruction: Union[str, List[str]]
    ) -> List[types.Part]:
        if not instruction:
            instruction = self._default_instruction()
        if isinstance(instruction, str):
            instruction = [instruction]
        return [types.Part.from_text(text=inst) for inst in instruction]

    def _default_instruction(self) -> str:
        return """You will be provided with some news that I have collected from RSS feeds and have formatted them. Provide them as a news feed to me. Write comprehensive paragraphs if you can expand on it. Make sure the feed is in English. Provide the news in a consistent format and include sources. The format should be as follows:

Use JSON. Each article has 3 fields: 
- title (string)
- summary (string)
- sources (array of strings). 

You should return an array of articles."""

    def _default_schema(self) -> genai.types.Schema:
        return genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["articles"],
            properties={
                "articles": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    items=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        required=["title", "summary", "sources"],
                        properties={
                            "title": genai.types.Schema(type=genai.types.Type.STRING),
                            "summary": genai.types.Schema(type=genai.types.Type.STRING),
                            "sources": genai.types.Schema(
                                type=genai.types.Type.ARRAY,
                                items=genai.types.Schema(type=genai.types.Type.STRING),
                            ),
                        },
                    ),
                ),
            },
        )

    def generate(self, prompt: str) -> dict:
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]

        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=5000),
            response_mime_type="application/json",
            response_schema=self.response_schema,
            system_instruction=self.system_instruction,
        )

        output = ""
        for chunk in self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=config,
        ):
            if chunk.text:
                output += chunk.text

        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON response: {e}\n\nRaw output:\n{output}"
            )
