from dataclasses import dataclass

from openai import OpenAI

# creates client and automatically fetches OPENAI_API_KEY from env variables
client = OpenAI()

test_repo = """--- Directory/test.py ---
print("Hello World from test directory!")


--- README.md ---
# Test_Repository

--- main.py ---
print("Hello World!")
"""


@dataclass
class Review:
    downsides_comments: str
    rating: str
    conclusion: str


def get_code_review(code, assigment, reviewed_level):
    downsides_comments_completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": "You are an expert on computer programing, "
                        "performing a code review of the provided code repository. "
                        f"Repository was writen by a {reviewed_level} programmer, "
                        "and should be held to corresponding standard."
                        f"Their assigment was: {assigment}"
                        "Your current task is to find downsides and write comments on the provided repository."},
            {"role": "user", "content": code}
        ]
    )

    rating_completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": "You are an expert on computer programing, "
                        "performing a code review of the provided code repository. "
                        f"Repository was writen by a {reviewed_level} programmer, "
                        "and should be held to corresponding standard"
                        f"Their assigment was: {assigment}"
                        "Your current task is to rate the provided repository on a scale from 0 to 100."
                        "You should be brief in your reasoning."},
            {"role": "user", "content": code},

            {"role": "assistant", "content": downsides_comments_completion.choices[0].message.content}
        ]
    )

    conclusion_completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": "You are an expert on computer programing, "
                        "performing a code review of the provided code repository. "
                        f"Repository was writen by a {reviewed_level} programmer, "
                        "and should be held to corresponding standard"
                        f"Their assigment was: {assigment}"
                        "Your current task is to draw conclusions on the provided code repository, and suggest ways to improve it."
                        "do not propose user to continue the conversation, this message is final in it"},
            {"role": "user", "content": code},

            {"role": "assistant", "content": downsides_comments_completion.choices[0].message.content},
            {"role": "assistant", "content": rating_completion.choices[0].message.content},
        ]
    )
    review = Review(
        downsides_comments=downsides_comments_completion.choices[0].message.content,
        rating=rating_completion.choices[0].message.content,
        conclusion=conclusion_completion.choices[0].message.content
    )

    return review


def main():
    review = get_code_review(test_repo, "write a hello world program", "Junior")

    # Print the code review
    print("Code Review:\n")
    for item in review:
        print(item)
    # print(review)


if __name__ == "__main__":
    main()
