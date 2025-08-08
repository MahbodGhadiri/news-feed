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

    def _default_instruction(self) -> List[str]:
        return [
            "You will be provided with a collection of news items formatted from RSS feeds.",
            "Your task is to summarize and polish the content you receive. Do not add or invent any new information.",
            "All output must be in English.",
            "The output should be in JSON format. Return an array of articles, where each article has the following fields:",
            "- title (string): a clear and concise English title.",
            "- summary (string): a polished and accurate English summary of the original content.",
            "- sources (array of strings): valid links to the original news sources.",
            "Only include articles that contain at least one valid source link. If an article does not contain a valid link, ignore it.",
            "Write comprehensive summaries when possible, but do not include information not present in the input.",
            "Ensure consistency and clarity throughout the output."
        ]


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
