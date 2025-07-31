import os
from langchain_google_genai import ChatGoogleGenerativeAI
import re

def clean_response(text):
    # Remove markdown bold/italic and excessive newlines
    text = re.sub(r"\*\*|\*", "", text)  # Remove * and **
    text = re.sub(r"\n{2,}", "\n", text)  # Replace multiple newlines with one
    text = text.strip()
    text = text.replace("\n", " ")
    return text
async def gemini_answer(context, question):
    api_key = os.getenv("GEMINI_API_KEY")
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.0,
        top_p=0.95,
        max_output_tokens=300,
        google_api_key=api_key
    )
    prompt = (
    "You are a senior insurance advisor. Read the following policy content carefully. "
    "Answer the user's question clearly and authoritatively, using only the provided context. "
    "If the answer is not directly present, use your insurance domain expertise to give a logical, likely response, without saying 'not mentioned' or 'not found'. "
    "Avoid technical or legal language—use plain, friendly explanations.\n\n"
    f"Context:\n{context}\n\n"
    f"Question: {question}"
)
 
    result = await llm.ainvoke(prompt)
    return clean_response(result.content)