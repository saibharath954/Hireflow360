"""
AI Service for resume parsing and message generation
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Modern LangChain Imports (LCEL)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI  # Updated from langchain.chat_models

from app.core.config import settings
from app.core.logging import logger


class AIService:
    """AI Service for intelligent processing using Modern LangChain (LCEL)"""
    
    # Common configuration for LLMs
    _openai_api_key = settings.OPENAI_API_KEY

    @staticmethod
    def _get_llm(temperature: float = 0.1, max_tokens: int = 1000) -> ChatOpenAI:
        """Helper to create LLM instance with proper API key handling"""
        return ChatOpenAI(
            api_key=AIService._openai_api_key,
            temperature=temperature,
            model="gpt-3.5-turbo",
            max_tokens=max_tokens
        )

    @staticmethod
    def parse_resume_with_llm(resume_text: str) -> Dict[str, Any]:
        """
        Parse resume text using LLM for better accuracy
        """
        try:
            prompt = PromptTemplate(
                input_variables=["resume_text"],
                template="""
                Extract structured information from this resume. Return ONLY valid JSON.
                
                Resume Text:
                {resume_text}
                
                Extract the following fields:
                1. name (string)
                2. email (string)
                3. phone (string or null)
                4. years_experience (integer or null)
                5. skills (array of strings)
                6. current_company (string or null)
                7. education (string or null)
                8. location (string or null)
                9. summary (string or null)
                
                Format the response as JSON with these exact keys.
                If a field cannot be found, use null.
                """
            )
            
            # LCEL Chain Construction: Prompt -> LLM -> String Output
            llm = AIService._get_llm(temperature=0.1, max_tokens=1000)
            chain = prompt | llm | StrOutputParser()
            
            # Split long resumes
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=3000,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
            
            chunks = text_splitter.split_text(resume_text)
            
            parsed_data = {}
            if len(chunks) > 1:
                # Process first chunk for basic info
                result1 = chain.invoke({"resume_text": chunks[0]})
                parsed_data.update(json.loads(result1))
                
                # Subsequent chunks for skills enrichment
                skills_set = set(parsed_data.get('skills', []))
                
                skills_prompt = PromptTemplate(
                    input_variables=["text"],
                    template="""
                    Extract ONLY technical/professional skills from this text.
                    Return as JSON array: {{"skills": ["skill1", "skill2"]}}
                    
                    Text: {text}
                    """
                )
                
                skills_chain = skills_prompt | llm | StrOutputParser()
                
                for chunk in chunks[1:]:
                    try:
                        skills_result = skills_chain.invoke({"text": chunk})
                        skills_data = json.loads(skills_result)
                        if 'skills' in skills_data:
                            skills_set.update(skills_data['skills'])
                    except Exception as e:
                        logger.warning(f"Error parsing skills chunk: {e}")
                        pass
                
                parsed_data['skills'] = list(skills_set)[:20]  # Limit to top 20
                
            else:
                result = chain.invoke({"resume_text": resume_text})
                parsed_data = json.loads(result)
            
            # Clean and validate data
            parsed_data = AIService._clean_parsed_data(parsed_data)
            
            # Calculate confidence scores
            confidence_scores = AIService._calculate_confidence_scores(parsed_data, resume_text)
            parsed_data['confidence_scores'] = confidence_scores
            
            logger.info(f"Successfully parsed resume with LLM")
            return parsed_data
            
        except Exception as e:
            logger.error(f"LLM parsing failed: {str(e)}")
            # Fallback to regex parsing
            return AIService._parse_resume_with_regex(resume_text)

    @staticmethod
    def generate_conversational_message(
        intent: str,
        candidate_info: Dict[str, Any],
        pending_fields: List[str],
        conversation_history: List[Dict[str, Any]]
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Generate human-like conversational message
        """
        try:
            prompt = PromptTemplate(
                input_variables=["intent", "candidate_info", "pending_fields", "conversation_history"],
                template="""
                You are a friendly HR recruiter reaching out to a candidate. Generate a SINGLE, 
                natural WhatsApp message based on the HR's intent.
                
                HR Intent: {intent}
                
                Candidate Information:
                Name: {candidate_info[name]}
                Current Company: {candidate_info[current_company]}
                Skills: {candidate_info[skills]}
                Experience: {candidate_info[years_experience]} years
                
                Information still needed (ask naturally, max 2-3 questions):
                {pending_fields}
                
                Previous conversation (if any):
                {conversation_history}
                
                Guidelines:
                1. Send ONE message only (not multiple messages)
                2. Use natural, conversational tone (like a real person)
                3. Address by first name
                4. Keep it concise (WhatsApp-appropriate length)
                5. Ask questions conversationally (not like a form)
                6. Acknowledge any information already provided
                7. Don't use bullet points or numbered lists
                8. Sound friendly and professional
                
                Return ONLY the message text.
                """
            )
            
            llm = AIService._get_llm(temperature=0.7, max_tokens=300)
            chain = prompt | llm | StrOutputParser()
            
            # Format conversation history
            history_text = ""
            for msg in conversation_history[-3:]:  # Last 3 messages
                direction = "You" if msg['direction'] == 'outgoing' else "Candidate"
                history_text += f"{direction}: {msg['content'][:100]}\n"
            
            message = chain.invoke({
                "intent": intent,
                "candidate_info": candidate_info,
                "pending_fields": ", ".join(pending_fields[:3]),  # Max 3 questions
                "conversation_history": history_text
            })
            
            # Extract which fields are being asked
            asked_fields = AIService._extract_asked_fields(message, pending_fields)
            
            metadata = {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "generated_at": datetime.utcnow().isoformat(),
                "tokens_estimated": len(message.split()) * 1.3
            }
            
            return message.strip(), asked_fields, metadata
            
        except Exception as e:
            logger.error(f"Message generation failed: {str(e)}")
            # Fallback logic remains same as original...
            first_name = candidate_info.get('name', '').split()[0] if candidate_info.get('name') else "there"
            fallback_message = f"Hi {first_name}! {intent}"
            
            if pending_fields:
                field_questions = {
                    'location': "May I know where you're currently based?",
                    'notice_period': "What's your notice period?",
                    'expected_salary': "Could you share your salary expectations?",
                    'availability': "When would you be available to start?"
                }
                questions = []
                for field in pending_fields[:2]:
                    if field in field_questions:
                        questions.append(field_questions[field])
                if questions:
                    fallback_message += " " + " ".join(questions)
            
            fallback_message += " Looking forward to hearing from you!"
            return fallback_message, pending_fields[:2], {"fallback": True}

    @staticmethod
    def analyze_candidate_reply(
        reply_text: str,
        candidate_info: Dict[str, Any],
        asked_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze candidate reply and extract information
        """
        try:
            prompt = PromptTemplate(
                input_variables=["reply_text", "candidate_info", "asked_fields"],
                template="""
                Analyze this candidate reply and extract structured information.
                
                Candidate Reply:
                {reply_text}
                
                Candidate Information (for context):
                Name: {candidate_info[name]}
                Current Status: {candidate_info[status]}
                
                Fields that were asked about:
                {asked_fields}
                
                Extract the following:
                1. Classification: 'interested', 'not_interested', 'question', 'needs_clarification'
                2. Extracted information (for asked fields)
                3. Whether the candidate asked any questions
                4. Suggested natural reply (if needed)
                
                Return as JSON with these keys:
                - classification
                - extracted_data (dict with field: value)
                - candidate_questions (array of questions asked)
                - requires_hr_review (boolean)
                - suggested_reply (string or null)
                - confidence_scores (dict with field: confidence)
                """
            )
            
            llm = AIService._get_llm(temperature=0.3, max_tokens=500)
            chain = prompt | llm | StrOutputParser()
            
            result = chain.invoke({
                "reply_text": reply_text,
                "candidate_info": candidate_info,
                "asked_fields": ", ".join(asked_fields)
            })
            
            analysis = json.loads(result)
            
            # Extract structured data with regex fallback
            extracted_data = analysis.get('extracted_data', {})
            
            # Enhance with regex extraction
            extracted_data.update(AIService._extract_structured_data_regex(reply_text))
            
            # Determine if HR review is needed
            requires_hr_review = analysis.get('requires_hr_review', False)
            
            # If candidate asked questions, flag for HR review
            if analysis.get('candidate_questions'):
                requires_hr_review = True
                if not analysis.get('suggested_reply'):
                    analysis['suggested_reply'] = AIService._generate_question_response(
                        analysis['candidate_questions']
                    )
            
            analysis['extracted_data'] = extracted_data
            analysis['requires_hr_review'] = requires_hr_review
            
            logger.info(f"Reply analyzed: {analysis.get('classification', 'unknown')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Reply analysis failed: {str(e)}")
            return AIService._analyze_reply_fallback(reply_text)

    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from text using LLM
        """
        try:
            prompt = PromptTemplate(
                input_variables=["text", "max_keywords"],
                template="""
                Extract the top {max_keywords} most important keywords or phrases from this text.
                Focus on skills, technologies, qualifications, and requirements.
                
                Text: {text}
                
                Return as JSON array: ["keyword1", "keyword2"]
                """
            )
            
            llm = AIService._get_llm(temperature=0.1, max_tokens=200)
            chain = prompt | llm | StrOutputParser()
            
            result = chain.invoke({
                "text": text[:2000],
                "max_keywords": max_keywords
            })
            
            keywords = json.loads(result)
            return keywords[:max_keywords]
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {str(e)}")
            # Simple word frequency fallback
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            from collections import Counter
            common_words = Counter(words).most_common(max_keywords)
            return [word for word, count in common_words]

    # --------------------------------------------------------------------------
    # Helper methods (Regex & Utilities) - Preserved from original
    # --------------------------------------------------------------------------
    
    @staticmethod
    def _clean_parsed_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize parsed data"""
        cleaned = data.copy()
        
        # Clean name
        if 'name' in cleaned and cleaned['name']:
            name = cleaned['name'].strip()
            name = re.sub(r'\s+', ' ', name)
            name = re.sub(r'^(Mr\.|Ms\.|Mrs\.|Dr\.|Prof\.)\s*', '', name, flags=re.IGNORECASE)
            cleaned['name'] = name.title()
        
        # Clean email
        if 'email' in cleaned and cleaned['email']:
            email = cleaned['email'].strip().lower()
            if '@' in email:
                cleaned['email'] = email
        
        # Clean phone
        if 'phone' in cleaned and cleaned['phone']:
            phone = ''.join(filter(str.isdigit, cleaned['phone']))
            if len(phone) >= 10:
                if phone.startswith('1') and len(phone) == 11:
                    cleaned['phone'] = f"+{phone[0]}-{phone[1:4]}-{phone[4:7]}-{phone[7:]}"
                elif len(phone) == 10:
                    cleaned['phone'] = f"+1-{phone[:3]}-{phone[3:6]}-{phone[6:]}"
            else:
                cleaned['phone'] = None
        
        # Clean years_experience
        if 'years_experience' in cleaned:
            try:
                years = int(cleaned['years_experience'])
                if 0 <= years <= 50:
                    cleaned['years_experience'] = years
                else:
                    cleaned['years_experience'] = None
            except:
                cleaned['years_experience'] = None
        
        # Clean skills
        if 'skills' in cleaned:
            skills = []
            for skill in cleaned['skills']:
                if isinstance(skill, str):
                    skill_clean = skill.strip()
                    if skill_clean and len(skill_clean) <= 50:
                        skills.append(skill_clean)
            seen = set()
            cleaned['skills'] = [skill for skill in skills if not (skill in seen or seen.add(skill))]
        
        return cleaned
    
    @staticmethod
    def _calculate_confidence_scores(data: Dict[str, Any], original_text: str) -> Dict[str, float]:
        scores = {}
        # Name confidence
        if data.get('name'):
            name_words = data['name'].split()
            if len(name_words) >= 2 and any(word.istitle() for word in name_words):
                scores['name'] = 0.95
            else:
                scores['name'] = 0.7
        else:
            scores['name'] = 0.0
        
        # Email confidence
        if data.get('email'):
            if '@' in data['email'] and '.' in data['email'].split('@')[1]:
                scores['email'] = 0.98
            else:
                scores['email'] = 0.5
        else:
            scores['email'] = 0.0
            
        return scores

    @staticmethod
    def _parse_resume_with_regex(resume_text: str) -> Dict[str, Any]:
        """Fallback regex parsing for resumes"""
        data = {
            'name': None, 'email': None, 'phone': None,
            'years_experience': None, 'skills': [],
            'current_company': None, 'education': None,
            'location': None, 'summary': None
        }
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, resume_text)
        if email_match:
            data['email'] = email_match.group(0)
            
        return data

    @staticmethod
    def _extract_asked_fields(message: str, possible_fields: List[str]) -> List[str]:
        """Extract which fields are being asked about in the message"""
        asked_fields = []
        field_keywords = {
            'location': ['where', 'location', 'based', 'city'],
            'notice_period': ['notice', 'period', 'start', 'availability'],
            'expected_salary': ['salary', 'compensation', 'package'],
            'experience': ['experience', 'years', 'background'],
            'skills': ['skills', 'technologies', 'expertise'],
        }
        message_lower = message.lower()
        for field in possible_fields:
            if field in field_keywords:
                if any(k in message_lower for k in field_keywords[field]):
                    asked_fields.append(field)
        return asked_fields

    @staticmethod
    def _extract_structured_data_regex(text: str) -> Dict[str, Any]:
        """Extract structured data using regex patterns"""
        data = {}
        # Simple extraction for robustness
        salary_patterns = [r'\$?(\d{2,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:k|K)?']
        for pattern in salary_patterns:
            match = re.search(pattern, text)
            if match:
                data['expected_salary'] = match.group(0)
                break
        return data

    @staticmethod
    def _generate_question_response(questions: List[str]) -> str:
        if not questions:
            return "Thanks for your response! Let me check on that."
        return "Thanks for your question! Let me get you the information you need. Could we schedule a quick call?"

    @staticmethod
    def _analyze_reply_fallback(reply_text: str) -> Dict[str, Any]:
        text_lower = reply_text.lower()
        classification = "interested"
        if any(w in text_lower for w in ['not interested', 'no thanks']):
            classification = "not_interested"
        elif '?' in text_lower:
            classification = "question"
        
        return {
            "classification": classification,
            "extracted_data": {},
            "candidate_questions": [],
            "requires_hr_review": classification == "question",
            "suggested_reply": None,
            "confidence_scores": {}
        }