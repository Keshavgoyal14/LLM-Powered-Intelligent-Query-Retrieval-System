import os
from langchain_google_genai import ChatGoogleGenerativeAI
import re
from typing import Tuple

def detect_domain(context: str, question: str) -> Tuple[str, str]:
    domain_keywords = {
        "insurance": [
            "policy", "coverage", "premium", "claim", "insurer", "policyholder",
            "benefits", "insurance", "deductible", "underwriting", "waiting period",
            "exclusion", "nominee", "dependents", "AYUSH", "NCD", "room rent",
            "sub-limit", "ambulance", "prosthesis", "cashless", "reimbursement",
            "hospitalization", "sum insured", "grievance", "pre-authorization",
            "network provider", "day care", "inpatient", "outpatient", "renewal",
            "endorsement", "IRDAI", "maternity", "PED", "No Claim Discount",
            "preventive health check-up", "medical expenses", "organ donor",
            "claim settlement", "health check-ups", "hospital", "AYUSH treatments"
        ],
        "legal": [
            "law", "regulation", "compliance", "legal", "statute", "jurisdiction",
            "rights", "obligations", "liability", "contract law", "grievance",
            "timeline", "procedure", "rejection", "appeal", "documentation",
            "enforcement", "precedent", "audit", "statutory", "filing"
        ],
        "hr": [
            "employee", "HR", "human resources", "employment", "workplace",
            "personnel", "staff", "hiring", "benefits", "leave policy",
            "group policy", "dependent", "addition", "eligibility", "documentation",
            "mid-policy", "coverage", "termination", "protocol"
        ],
        "contracts": [
            "agreement", "contract", "party", "clause", "term", "obligation",
            "binding", "execution", "termination", "parties", "performance",
            "breach", "remedy", "indemnification", "warranty", "dispute",
            "resolution", "structure", "provision"
        ],
        "general": [
            "university", "Newton", "grandfather", "descendant", "science",
            "algorithm", "test case", "source code", "database", "password",
            "secret code", "customer care", "chat log", "employee list",
            "personal details", "fraud", "forged", "manipulate", "illegal",
            "automatically approve", "backend", "contact details"
        ]
    }

    full_text = f"{context.lower()} {question.lower()}"
    domain_scores = {
        domain: sum(1 for keyword in keywords if keyword in full_text)
        for domain, keywords in domain_keywords.items()
    }
    detected_domain = max(domain_scores.items(), key=lambda x: x[1])[0]
    roles = {
        "insurance": "senior insurance advisor",
        "legal": "legal compliance specialist",
        "hr": "human resources professional",
        "contracts": "contract management expert",
        "general": "general information assistant"
    }
    return detected_domain, roles[detected_domain]

def is_safe_and_relevant(domain: str, question: str) -> bool:
    forbidden_keywords = [
        "password", "secret code", "database", "contact details",
        "chat log", "personal details", "illegal", "manipulate", "forged", "fraud"
    ]
    question_lower = question.lower()
    if domain == "general" or any(bad in question_lower for bad in forbidden_keywords):
        return False
    return True

def clean_response(text: str) -> str:
    # Remove markdown bold/italic and excessive newlines
    text = re.sub(r"\*\*|\*", "", text)  # Remove * and **
    text = re.sub(r"\n{2,}", ".", text)  # Replace multiple newlines with one
    text = text.strip()
    text = text.replace("\n", " ")
    return text

async def gemini_answer(context: str, question: str):
    api_key = os.getenv("GEMINI_API_KEY")
    
    # Detect domain and role automatically
    domain, role = detect_domain(context, question)
    if not is_safe_and_relevant(domain, question):
        return ("Sorry, this question cannot be answered as it is outside the scope of "
                "insurance/legal/HR/contract information or violates privacy/security guidelines.")

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro", 
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
                     "warranties, and dispute resolution mechanisms"),
        "general": ("general knowledge, science, history, and public information")
    }

    # Choose prompt based on domain
    if domain == "general":
        prompt = (
            "You are a knowledgeable assistant. "
            "Answer the following question using only the provided context . "
            "If the context does not contain the answer, use your general knowledge. "
            "Be clear, concise, and factual. If the question is about programming, provide a code example if possible.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )
    else:
        prompt = (
            f"You are a {role} with extensive expertise in {domain_expertise[domain]}. "
            "Analyze the provided content carefully and professionally.\n\n"
            "REQUIREMENTS:\n"
            "1. Be concise, clear and direct\n"
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
        print(f"Gemini response: {result.content}")
        return clean_response(result.content)
    except Exception as e:
        return f"Error generating response: {str(e)}"