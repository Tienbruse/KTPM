import os
import getpass

from langchain_deepseek import ChatDeepSeek

def main():
    llm = ChatDeepSeek(
        model="deepseek-chat",  
        api_key="sk-48e7b76b373a4527ba461b2f78848cea",    
        temperature=0.7,            
        max_tokens=None,            
        timeout=None,               
        max_retries=2,             
    )

    messages = [
        (
            "system",
            "You are a helpful assistant.",
        ),
        ("human", "Bạn là ai ?"),
    ]

    response = llm.invoke(messages)
    print("Assistant response:", response.content)

    from langchain_core.prompts import ChatPromptTemplate
    prompt = ChatPromptTemplate(
        [
            ("system", "You are a helpful assistant that translates {input_language} to {output_language}."),
            ("human", "{input}"),
        ]
    )
    chain = prompt | llm
    chain_response = chain.invoke(
        {
            "input_language": "English",
            "output_language": "Vietnamese",
            "input": "I love programming.",
        }
    )
    print("Assistant chain response:", chain_response.content)


if __name__ == "__main__":
    main()
