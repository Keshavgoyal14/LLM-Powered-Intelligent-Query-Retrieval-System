import os
from langchain_google_genai import ChatGoogleGenerativeAI
import re
from typing import Tuple

def detect_domain(context: str, question: str) -> Tuple[str, str]:
    # Keywords for domain detection
    domain_keywords = {
        "insurance": [
            "policy", "coverage", "premium", "claim", "insurer", "policyholder",
            "benefits", "insurance", "deductible", "underwriting"
        ],
        "legal": [
            "law", "regulation", "compliance", "legal", "statute", "jurisdiction",
            "rights", "obligations", "liability", "contract law"
        ],
        "hr": [
            "employee", "HR", "human resources", "employment", "workplace",
            "personnel", "staff", "hiring", "benefits", "leave policy"
        ],
        "contracts": [
            "agreement", "contract", "party", "clause", "term", "obligation",
            "binding", "execution", "termination", "parties"
        ]
    }

    # Combine context and question for analysis
    full_text = f"{context.lower()} {question.lower()}"
    
    # Count domain-specific keywords
    domain_scores = {
        domain: sum(1 for keyword in keywords if keyword in full_text)
        for domain, keywords in domain_keywords.items()
    }
    
    # Get domain with highest score
    detected_domain = max(domain_scores.items(), key=lambda x: x[1])[0]
    
    # Get domain-specific role
    roles = {
        "insurance": "senior insurance advisor",
        "legal": "legal compliance specialist",
        "hr": "human resources professional",
        "contracts": "contract management expert"
    }
    
    return detected_domain, roles[detected_domain]

def clean_response(text: str) -> str:
    # Remove markdown bold/italic and excessive newlines
    text = re.sub(r"\*\*|\*", "", text)  # Remove * and **
    text = re.sub(r"\n{2,}", "\n", text)  # Replace multiple newlines with one
    text = text.strip()
    text = text.replace("\n", " ")
    return text

async def gemini_answer(context: str, question: str):
    api_key = os.getenv("GEMINI_API_KEY")
    
    # Detect domain and role automatically
    domain, role = detect_domain(context, question)
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.0,
        top_p=0.95,
        max_output_tokens=300,
        google_api_key=api_key
    )

    domain_expertise = {
        "insurance": ("insurance policies, coverage terms, claims processing, "
                     "underwriting standards, policy exclusions, waiting periods, "
                     "regulatory compliance, risk assessment, benefit calculations, "
                     "premium structures, and IRDAI guidelines"),
        "legal": ("regulations, compliance requirements, legal frameworks, "
                 "statutory interpretations, jurisdictional requirements, "
                 "legal precedents, liability assessments, regulatory filings, "
                 "enforcement procedures, and compliance auditing"),
        "hr": ("HR policies, employee relations, workplace regulations, "
               "compensation structures, benefit administration, leave management, "
               "performance evaluation, workplace safety, talent acquisition, "
               "training programs, and labor law compliance"),
        "contracts": ("contractual terms, obligations, agreement structures, "
                     "liability clauses, performance conditions, breach remedies, "
                     "termination provisions, indemnification clauses, "
                     "warranties, and dispute resolution mechanisms")
    }


    prompt = (
        f"You are a {role} with extensive expertise in {domain_expertise[domain]}. "
        "Analyze the provided content carefully and professionally.\n\n"
        "REQUIREMENTS:\n"
         "1. Be concise,clear and direct\n"
        "2. Use ONLY information from the provided context\n"
        "3. Include specific details (dates, numbers, terms) when present\n"
        "4. If information isn't explicit, provide logical domain-specific insights\n"
        "5. Use clear, accessible language\n"
        "6. Format response professionally\n"
        "7. Highlight any regulatory or compliance aspects\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Professional Response:"
    )

    try:
        result = await llm.ainvoke(prompt)
        return clean_response(result.content)
    except Exception as e:
        return f"Error generating response: {str(e)}"