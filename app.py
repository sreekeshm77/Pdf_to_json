import streamlit as st
import PyPDF2
import json
import re
import tempfile
import os

class EnhancedResumeParser:
    def __init__(self):
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_pattern = re.compile(r'[\+]?[0-9]{10,13}')
        
    def extract_text(self, pdf_file):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf_file.getvalue())
                temp_path = temp_file.name

            text = ""
            with open(temp_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"

            os.remove(temp_path)
            return text
        except Exception as e:
            st.error(f"Error processing PDF: {str(e)}")
            return None

    def fix_text_spacing(self, text):
        """Fix text spacing issues from PDF extraction"""
        # Add spaces before capital letters that follow lowercase letters
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        # Fix common patterns
        text = text.replace('•', ' • ')
        text = text.replace('|', ' | ')
        return text

    def parse_resume(self, raw_text):
        if not raw_text:
            return None

        # Fix spacing issues
        text = self.fix_text_spacing(raw_text)
        
        # Initialize the structured data
        parsed_data = {
            "name": "",
            "profession": "",
            "email": "",
            "phone": "",
            "links": {
                "linkedin": "",
                "github": "",
                "portfolio": "",
                "other": []
            },
            "summary": "",
            "skills": {
                "programming_languages": [],
                "tools": [],
                "data_science": [],
                "machine_learning": [],
                "frameworks": [],
                "all": []
            },
            "work_experience": [],
            "projects": [],
            "certifications": [],
            "education": [],
            "raw_text": raw_text[:1000]  # Keep first 1000 chars for reference
        }

        # Extract name and profession from first line
        first_line_match = re.search(r'^([A-Z\s]+)([A-Z][a-z]+)?.*?[|/](.+?)(?:\+|•|$)', text)
        if first_line_match:
            # Extract name
            name_part = first_line_match.group(1).strip()
            if first_line_match.group(2):
                name_part += first_line_match.group(2)
            parsed_data["name"] = self.clean_name(name_part)
            
            # Extract profession
            profession_part = first_line_match.group(3)
            profession_cleaned = re.sub(r'[+•].*', '', profession_part).strip()
            parsed_data["profession"] = profession_cleaned

        # Extract email
        email_match = self.email_pattern.search(text)
        if email_match:
            parsed_data["email"] = email_match.group()

        # Extract phone
        phone_match = self.phone_pattern.search(text)
        if phone_match:
            parsed_data["phone"] = "+" + phone_match.group().lstrip('+')

        # Extract links
        if 'LinkedIn' in text or 'linkedin' in text:
            parsed_data["links"]["linkedin"] = "LinkedIn profile found"
        if 'GitHub' in text or 'github' in text:
            parsed_data["links"]["github"] = "GitHub profile found"
        if 'Portfolio' in text or 'portfolio' in text:
            parsed_data["links"]["portfolio"] = "Portfolio found"

        # Extract summary
        summary_match = re.search(r'SUMMAR\s*Y\s*(.+?)(?=SKILLS|EXPERIENCE|EDUCATION|PROJECTS|$)', text, re.DOTALL | re.IGNORECASE)
        if summary_match:
            summary_text = summary_match.group(1).strip()
            # Fix spacing in summary
            summary_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', summary_text)
            parsed_data["summary"] = summary_text

        # Extract skills
        skills_match = re.search(r'SKILLS\s*(.+?)(?=EXPERIENCE|EDUCATION|PROJECTS|CERTIFICATIONS|$)', text, re.DOTALL | re.IGNORECASE)
        if skills_match:
            skills_text = skills_match.group(1)
            
            # Programming Languages & Tools
            prog_match = re.search(r'Programming\s*Languages?\s*&?\s*Tools?:?\s*([^•\n]+)', skills_text, re.IGNORECASE)
            if prog_match:
                skills_list = [s.strip() for s in prog_match.group(1).split(',')]
                parsed_data["skills"]["programming_languages"] = skills_list
                parsed_data["skills"]["all"].extend(skills_list)
            
            # Data Science & Analytics
            ds_match = re.search(r'Data\s*Science\s*&?\s*Analytics?:?\s*([^•\n]+)', skills_text, re.IGNORECASE)
            if ds_match:
                skills_list = [s.strip() for s in ds_match.group(1).split(',')]
                parsed_data["skills"]["data_science"] = skills_list
                parsed_data["skills"]["all"].extend(skills_list)
            
            # Machine Learning & AI
            ml_match = re.search(r'Machine\s*Learning\s*&?\s*AI?:?\s*([^•\n]+)', skills_text, re.IGNORECASE)
            if ml_match:
                skills_list = [s.strip() for s in ml_match.group(1).split(',')]
                parsed_data["skills"]["machine_learning"] = skills_list
                parsed_data["skills"]["all"].extend(skills_list)
            
            # Frameworks & Libraries
            fw_match = re.search(r'Frameworks?\s*&?\s*Libraries?:?\s*([^•\n]+)', skills_text, re.IGNORECASE)
            if fw_match:
                skills_list = [s.strip() for s in fw_match.group(1).split(',')]
                parsed_data["skills"]["frameworks"] = skills_list
                parsed_data["skills"]["all"].extend(skills_list)

        # Extract work experience
        exp_match = re.search(r'(?:WORK\s*)?EXPERIENCE\s*(.+?)(?=EDUCATION|PROJECTS|SKILLS|CERTIFICATIONS|$)', text, re.DOTALL | re.IGNORECASE)
        if exp_match:
            exp_text = exp_match.group(1).strip()
            # Split by common job separators
            experiences = re.split(r'\n(?=\d{4}|[A-Z][a-z]+ \d{4})', exp_text)
            parsed_data["work_experience"] = [exp.strip() for exp in experiences if exp.strip()]

        # Extract education
        edu_match = re.search(r'EDUCATION\s*(.+?)(?=EXPERIENCE|PROJECTS|SKILLS|CERTIFICATIONS|$)', text, re.DOTALL | re.IGNORECASE)
        if edu_match:
            edu_text = edu_match.group(1).strip()
            # Split by degree types or years
            educations = re.split(r'\n(?=Bachelor|Master|PhD|Diploma|\d{4})', edu_text)
            parsed_data["education"] = [edu.strip() for edu in educations if edu.strip()]

        # Extract projects
        proj_match = re.search(r'PROJECTS?\s*(.+?)(?=EDUCATION|EXPERIENCE|SKILLS|CERTIFICATIONS|$)', text, re.DOTALL | re.IGNORECASE)
        if proj_match:
            proj_text = proj_match.group(1).strip()
            projects = re.split(r'\n(?=[A-Z][a-z]+)', proj_text)
            parsed_data["projects"] = [proj.strip() for proj in projects if proj.strip()]

        # Extract certifications
        cert_match = re.search(r'CERTIFICATIONS?\s*(.+?)(?=EDUCATION|EXPERIENCE|PROJECTS|SKILLS|$)', text, re.DOTALL | re.IGNORECASE)
        if cert_match:
            cert_text = cert_match.group(1).strip()
            certifications = cert_text.split('\n')
            parsed_data["certifications"] = [cert.strip() for cert in certifications if cert.strip()]

        return parsed_data

    def clean_name(self, name):
        """Clean and format name properly"""
        # Remove extra spaces and format properly
        name = re.sub(r'\s+', ' ', name)
        # Handle cases like "SREEKESHMAI" -> "Sreekesh Mai" or "Sreekesh M"
        if name.isupper() and len(name) > 10:
            # Try to split camelCase
            name = re.sub(r'([A-Z])([A-Z]+)', r'\1\2', name)
        return name.title()

def main():
    st.set_page_config(
        page_title="Resume Parser - Structured JSON",
        page_icon="📄",
        layout="wide"
    )

    st.title("📄 Resume Parser - Structured JSON Output")
    st.write("Upload a PDF resume to extract structured information")

    uploaded_file = st.file_uploader("Choose a PDF file", type=['pdf'])

    if uploaded_file is not None:
        parser = EnhancedResumeParser()

        with st.spinner('Extracting text from PDF...'):
            raw_text = parser.extract_text(uploaded_file)

        if raw_text:
            with st.spinner('Parsing resume information...'):
                results = parser.parse_resume(raw_text)

            if results:
                # Display parsed information
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.subheader("📋 Parsed Information")
                    
                    # Personal Info
                    st.markdown("### Personal Information")
                    st.write(f"**Name:** {results['name']}")
                    st.write(f"**Profession:** {results['profession']}")
                    st.write(f"**Email:** {results['email']}")
                    st.write(f"**Phone:** {results['phone']}")
                    
                    # Links
                    if any(results['links'].values()):
                        st.markdown("### 🔗 Links")
                        for key, value in results['links'].items():
                            if value and key != 'other':
                                st.write(f"**{key.title()}:** {value}")
                    
                    # Summary
                    if results['summary']:
                        st.markdown("### 📝 Summary")
                        st.write(results['summary'])
                    
                    # Work Experience
                    if results['work_experience']:
                        st.markdown("### 💼 Work Experience")
                        for i, exp in enumerate(results['work_experience'], 1):
                            st.write(f"{i}. {exp}")
                    
                    # Education
                    if results['education']:
                        st.markdown("### 🎓 Education")
                        for edu in results['education']:
                            st.write(f"• {edu}")

                with col2:
                    # Skills
                    if results['skills']['all']:
                        st.markdown("### 🔧 Skills")
                        
                        if results['skills']['programming_languages']:
                            st.write("**Programming Languages & Tools:**")
                            st.write(", ".join(results['skills']['programming_languages']))
                        
                        if results['skills']['data_science']:
                            st.write("**Data Science & Analytics:**")
                            st.write(", ".join(results['skills']['data_science']))
                        
                        if results['skills']['machine_learning']:
                            st.write("**Machine Learning & AI:**")
                            st.write(", ".join(results['skills']['machine_learning']))
                        
                        if results['skills']['frameworks']:
                            st.write("**Frameworks & Libraries:**")
                            st.write(", ".join(results['skills']['frameworks']))
                    
                    # Projects
                    if results['projects']:
                        st.markdown("### 🚀 Projects")
                        for proj in results['projects']:
                            st.write(f"• {proj}")
                    
                    # Certifications
                    if results['certifications']:
                        st.markdown("### 🏆 Certifications")
                        for cert in results['certifications']:
                            st.write(f"• {cert}")

                # Download structured JSON
                st.markdown("---")
                st.subheader("⬇️ Download Structured JSON")
                
                # Remove raw_text from download to keep file clean
                download_data = {k: v for k, v in results.items() if k != 'raw_text'}
                json_str = json.dumps(download_data, indent=2)
                
                # Generate filename
                filename = f"{results['name'].replace(' ', '_').lower()}_resume.json" if results['name'] else "parsed_resume.json"
                
                st.download_button(
                    label="Download Structured JSON",
                    file_name=filename,
                    mime="application/json",
                    data=json_str
                )

                # Show JSON preview
                with st.expander("Preview JSON Output"):
                    st.json(download_data)

    # Sidebar
    with st.sidebar:
        st.header("📊 JSON Structure")
        st.code('''{
  "name": "Full Name",
  "profession": "Job Title",
  "email": "email@example.com",
  "phone": "+1234567890",
  "links": {
    "linkedin": "URL",
    "github": "URL",
    "portfolio": "URL",
    "other": []
  },
  "summary": "Professional summary...",
  "skills": {
    "programming_languages": [],
    "tools": [],
    "data_science": [],
    "machine_learning": [],
    "frameworks": [],
    "all": []
  },
  "work_experience": [],
  "projects": [],
  "certifications": [],
  "education": []
}''')

if __name__ == "__main__":
    main()