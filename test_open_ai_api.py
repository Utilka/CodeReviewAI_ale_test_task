from openai import OpenAI
import os

# Set your OpenAI API key



def get_code_review(code):
    client = OpenAI()

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
    )

    print(completion.choices[0].message)

    # review = chat_completion['choices'][0]['message']['content']
    # return review

if __name__ == "__main__":
    # Replace 'your_code_file.py' with the path to your code file
    code_file_path = 'main.py'

    # Read code from the specified file
    try:
        with open(code_file_path, 'r') as file:
            code = file.read()
    except FileNotFoundError:
        print(f"Error: The file '{code_file_path}' was not found.")
        exit(1)

    # Get the code review from GPT-4 Turbo
    review = get_code_review(code)

    # Print the code review
    print("Code Review:\n")
    print(review)