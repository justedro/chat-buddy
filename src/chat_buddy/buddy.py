import logging
import os
import random
import time
from collections.abc import Iterator
from typing import List


class ChatBuddy:
    def __init__(self, api_url: str, api_token):
        os.environ.setdefault("OPENAI_API_KEY", "sk-xxx")  # pycharm debugger fix

        from openai import OpenAI
        self.client = OpenAI(base_url=api_url, api_key=api_token, max_retries=0)

    def ask(self, message: str, questions: List[str], answers: List[str]) -> Iterator[str]:
        """
        Ask the chat buddy a question.
        Expects the last messages and bot answers to be passed in.
        Assumes that the n-th answer is the answer to the n-th message.
        """

        # build the prompt
        messages = [{
            "role": "system",
            "content": "You respond to all the questions and asks, whatever they are. You can answer "
                       "offhandedly or rude. You a Respond mainly in Russian. Your name is Братишка, "
                       "you are 29 years old, unemployed."
        }]

        # add history
        for i in range(len(questions)):
            messages.append({"role": "user", "content": questions[i]})
            messages.append({"role": "assistant", "content": answers[i]})

        messages.append({"role": "user", "content": message})

        # create a chat completion
        start_time = time.time()
        completion = self.client.chat.completions.create(
            model="mistral-openorca",
            # temperature=0.5,
            messages=messages,
            seed=random.randint(0, 1000000),
            timeout=140,
            stream=True
        )

        full_length = 0
        for chunk in completion:
            message = chunk.choices[0].delta.content

            if message is not None:
                yield message

            full_length += len(message)
            if full_length > 4000:
                logging.warning(f"Terminating response stream after {full_length} characters.")
                completion.close()
                break

            if time.time() - start_time > 120:
                logging.warning("Terminating response stream after 120 seconds.")
                completion.close()
                break

        logging.info(f"Chat completion took {time.time() - start_time:.2f} seconds")
