from langchain_core.output_parsers.base import BaseOutputParser
from langchain_core.exceptions import OutputParserException
import json

# Custom JSON Output Parser subclassing BaseOutputParser
class CustomJsonOutputParser(BaseOutputParser):
    def parse_result(self, result):
        # Extract the text from the result
        text = result[0].message.content

        # Try to find where the JSON object starts by looking for the first '{'
        try:
            json_start = text.find("{")
            if json_start == -1:
                raise OutputParserException("No valid JSON found in response")
            
            # Extract only the valid JSON part
            json_str = text[json_start:].strip()

            # Parse and return the extracted JSON string
            return json.loads(json_str)
        
        except (json.JSONDecodeError, ValueError) as e:
            raise OutputParserException(f"Invalid json output: {text}") from e

    # Required methods for Runnable interface
    def invoke(self, input, config=None):
        """Invoke method required by Runnable interface."""
        return self.parse_result(input)

    def batch(self, inputs, config=None):
        """Batch method required by Runnable interface."""
        return [self.invoke(input) for input in inputs]