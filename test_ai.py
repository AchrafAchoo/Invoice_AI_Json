from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from io import StringIO
import sys
import os
import re
import json
from datetime import datetime
import google.generativeai as genai

def convert_pdf_to_txt(path):
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = open(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos=set()

    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password,caching=caching, check_extractable=True):
        interpreter.process_page(page)

    text = retstr.getvalue()

    fp.close()
    device.close()
    retstr.close()
    return text

def get_available_gemini_model():
    print("Checking available Gemini models...")
    
    preferred_models = [
        "models/gemini-1.5-flash",
        "models/gemini-1.5-pro", 
        "models/gemini-1.0-pro",
        "models/gemini-pro"
    ]
    
    try:
        available_models = []
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                available_models.append(m.name)
        
        print(f"Found {len(available_models)} suitable models")
        
        for preferred in preferred_models:
            if preferred in available_models:
                print(f"Selected preferred model: {preferred}")
                return preferred
        
        if available_models:
            selected = available_models[0]
            print(f"Using first available model: {selected}")
            return selected
            
        print("No suitable Gemini model supporting 'generateContent' found.")
        return None
        
    except Exception as e:
        print(f"Error listing Gemini models: {e}")
        return None

def ai_extract_invoice_data(text):
    
    try:
        api_key = os.environ.get("GOOGLE_API_KEY") 
        if not api_key:
            # Replace 'your_api_key_here' with your actual API key for testing
            api_key = "your_api_key_here"
            print("Warning: Using hardcoded API key. Consider setting GOOGLE_API_KEY environment variable for production.")

        genai.configure(api_key=api_key) 

        model_name = get_available_gemini_model()
        if not model_name:
            return {
                "invoice_number": None,
                "billing_date": None,
                "due_date": None,
                "total_ttc": None,
                "total_ht": None,
                "tva_amount": None,
                "company_info": {"name": None, "address": None, "phone": None, "email": None, "ice": None},
                "client_info": {"name": None, "address": None},
                "bank_info": {"bank_name": None, "iban": None, "rib": None},
                "articles": [],
                "error": "No suitable Gemini model found to perform extraction."
            }
        
        model = genai.GenerativeModel(model_name)

        prompt = f"""
        Analyze this invoice text and extract ALL the following information. Be very careful and precise:

        1. Invoice Number
        2. Billing Date
        3. Due Date
        4. Total TTC (final amount including tax)
        5. TVA/VAT amount
        6. Subtotal HT (amount before tax)
        7. Company/Seller Information (name, address, phone, email, ICE, etc.)
        8. Client/Customer Information (name, address)
        9. Bank Information (bank name, IBAN, RIB if present)
        10. Articles/Items purchased with details (description, quantity, unit price, total price, TVA rate)

        Return the result in this exact JSON format:
        {{
            "invoice_number": "found number or null",
            "billing_date": "date or null",
            "due_date": "date or null",
            "total_ttc": "amount without currency symbol or null",
            "total_ht": "amount without currency symbol or null", 
            "tva_amount": "amount without currency symbol or null",
            "company_info": {{
                "name": "company name or null",
                "address": "full address or null",
                "phone": "phone number or null",
                "email": "email or null",
                "ICE": "ICE number or null"
            }},
            "client_info": {{
                "name": "client name or null",
                "address": "client address or null"
            }},
            "bank_info": {{
                "bank_name": "bank name or null",
                "iban": "IBAN or null",
                "rib": "RIB or null"
            }},
            "articles": [
                {{
                    "description": "item description",
                    "quantity": "quantity or null",
                    "unit_price": "unit price or null",
                    "total_price": "total price or null",
                    "tva_rate": "TVA percentage or null"
                }}
            ]
        }}

        Invoice Text:
        {text[:4000]}
        """

        response = model.generate_content(prompt)
        
        result = response.text.strip()
        
        try:
            json_text = result
            
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                parts = json_text.split("```")
                if len(parts) >= 3:
                    json_text = parts[1].strip()
            
            data = json.loads(json_text)
            return data
            
        except json.JSONDecodeError as e:
            import re
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, result, re.DOTALL)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    if "invoice_number" in data or "total_ttc" in data:
                        return data
                except:
                    continue
            
            return {
                "invoice_number": None,
                "billing_date": None,
                "due_date": None,
                "total_ttc": None,
                "total_ht": None,
                "tva_amount": None,
                "company_info": {"name": None, "address": None, "phone": None, "email": None, "ICE": None},
                "client_info": {"name": None, "address": None},
                "bank_info": {"bank_name": None, "iban": None, "rib": None},
                "articles": [],
                "error": f"Failed to parse AI response. Raw response: {result[:200]}..."
            }
            
    except Exception as e:
        return {
            "invoice_number": None,
            "billing_date": None,
            "due_date": None,
            "total_ttc": None,
            "total_ht": None,
            "tva_amount": None,
            "company_info": {"name": None, "address": None, "phone": None, "email": None, "ICE": None},
            "client_info": {"name": None, "address": None},
            "bank_info": {"bank_name": None, "iban": None, "rib": None},
            "articles": [],
            "error": f"AI extraction failed: {str(e)}"
        }

def format_extraction_date():
    return datetime(2025, 7, 10).strftime("%d/%m/%Y")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_ai.py <pdf_filename>")
        print("Example: python test_ai.py modele_de_facture.pdf")
        print("For files with spaces: python test_ai.py \"file with spaces.pdf\"")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File '{pdf_path}' not found!")
        print("Make sure the file exists in the current directory.")
        print("For files with spaces in the name, use quotes around the filename.")
        sys.exit(1)
    
    try:
        print("Starting PDF to text conversion...")
        print(f"Processing file: {pdf_path}")
        
        extracted_text = convert_pdf_to_txt(pdf_path)
        
        print("\n🤖 Using Gemini AI to analyze invoice...")
        ai_results = ai_extract_invoice_data(extracted_text)
        
        print("\n" + "="*60)
        print("🤖 GEMINI AI-POWERED INVOICE ANALYSIS")
        print("="*60)
        
        if ai_results.get("error"):
            print(f"❌ AI Error: {ai_results['error']}")
        else:
            print("-" * 60)
            
            print(f"📄 Numéro de Facture: {ai_results.get('invoice_number') or 'Non trouvé'}")
            print(f"📅 Date de Facturation: {ai_results.get('billing_date') or 'Non trouvé'}")
            print(f"⏰ Date d'Échéance: {ai_results.get('due_date') or 'Non trouvé'}")
            print(f"� Total TTC: {ai_results.get('total_ttc') or 'Not found'} {'€' if ai_results.get('total_ttc') else ''}")
            print(f"� Total HT: {ai_results.get('total_ht') or 'Not found'} {'€' if ai_results.get('total_ht') else ''}")
            print(f"🧾 TVA Amount: {ai_results.get('tva_amount') or 'Not found'} {'€' if ai_results.get('tva_amount') else ''}")
            
            print(f"\n🏢 COMPANY INFO:")
            company = ai_results.get('company_info', {})
            print(f"  Name: {company.get('name') or 'Not found'}")
            print(f"  Address: {company.get('address') or 'Not found'}")
            print(f"  Phone: {company.get('phone') or 'Not found'}")
            print(f"  Email: {company.get('email') or 'Not found'}")
            print(f"  ICE: {company.get('ICE') or 'Not found'}")
            
            print(f"\n👤 CLIENT INFO:")
            client = ai_results.get('client_info', {})
            print(f"  Name: {client.get('name') or 'Not found'}")
            print(f"  Address: {client.get('address') or 'Not found'}")
            
            print(f"\n� BANK INFO:")
            bank = ai_results.get('bank_info', {})
            print(f"  Bank Name: {bank.get('bank_name') or 'Not found'}")
            print(f"  IBAN: {bank.get('iban') or 'Not found'}")
            print(f"  RIB: {bank.get('rib') or 'Not found'}")
            
            print(f"\n🛒 ARTICLES:")
            articles = ai_results.get('articles', [])
            if articles:
                for i, article in enumerate(articles, 1):
                    print(f"  {i}. {article.get('description') or 'No description'}")
                    print(f"     Quantity: {article.get('quantity') or 'N/A'}")
                    print(f"     Unit Price: {article.get('unit_price') or 'N/A'} {'€' if article.get('unit_price') else ''}")
                    print(f"     Total Price: {article.get('total_price') or 'N/A'} {'€' if article.get('total_price') else ''}")
                    print(f"     TVA Rate: {article.get('tva_rate') or 'N/A'}{'%' if article.get('tva_rate') else ''}")
                    print()
            else:
                print("  No articles found")
        
        print("="*60)
        
        print("\n--- First 500 characters of extracted text ---")
        print(extracted_text[:500])
        print("...")
        
        output_folder = "text save"
        analysis_folder = "analysis"
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        if not os.path.exists(analysis_folder):
            os.makedirs(analysis_folder)
        
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_file = os.path.join(output_folder, f"{pdf_name}_extracted.txt")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        invoice_file = os.path.join(analysis_folder, f"{pdf_name}_gemini_analysis.txt")
        with open(invoice_file, 'w', encoding='utf-8') as f:
            f.write("GEMINI AI-POWERED INVOICE ANALYSIS\n")
            f.write("="*40 + "\n\n")
            
            if ai_results.get("error"):
                f.write(f"ERROR: {ai_results['error']}\n\n")
            else:
                f.write(f"Invoice Number: {ai_results.get('invoice_number') or 'Not found'}\n")
                f.write(f"Billing Date: {ai_results.get('billing_date') or 'Not found'}\n")
                f.write(f"Due Date: {ai_results.get('due_date') or 'Not found'}\n")
                f.write(f"Total TTC: {ai_results.get('total_ttc') or 'Not found'} {'€' if ai_results.get('total_ttc') else ''}\n")
                f.write(f"Total HT: {ai_results.get('total_ht') or 'Not found'} {'€' if ai_results.get('total_ht') else ''}\n")
                f.write(f"TVA Amount: {ai_results.get('tva_amount') or 'Not found'} {'€' if ai_results.get('tva_amount') else ''}\n\n")
                
                f.write("COMPANY INFO:\n")
                company = ai_results.get('company_info', {})
                f.write(f"  Name: {company.get('name') or 'Not found'}\n")
                f.write(f"  Address: {company.get('address') or 'Not found'}\n")
                f.write(f"  Phone: {company.get('phone') or 'Not found'}\n")
                f.write(f"  Email: {company.get('email') or 'Not found'}\n")
                f.write(f"  ICE: {company.get('ICE') or 'Not found'}\n\n")
                
                f.write("CLIENT INFO:\n")
                client = ai_results.get('client_info', {})
                f.write(f"  Name: {client.get('name') or 'Not found'}\n")
                f.write(f"  Address: {client.get('address') or 'Not found'}\n\n")
                
                f.write("BANK INFO:\n")
                bank = ai_results.get('bank_info', {})
                f.write(f"  Bank Name: {bank.get('bank_name') or 'Not found'}\n")
                f.write(f"  IBAN: {bank.get('iban') or 'Not found'}\n")
                f.write(f"  RIB: {bank.get('rib') or 'Not found'}\n\n")
                
                f.write("ARTICLES:\n")
                articles = ai_results.get('articles', [])
                if articles:
                    for i, article in enumerate(articles, 1):
                        f.write(f"  {i}. {article.get('description') or 'No description'}\n")
                        f.write(f"     Quantity: {article.get('quantity') or 'N/A'}\n")
                        f.write(f"     Unit Price: {article.get('unit_price') or 'N/A'} {'€' if article.get('unit_price') else ''}\n")
                        f.write(f"     Total Price: {article.get('total_price') or 'N/A'} {'€' if article.get('total_price') else ''}\n")
                        f.write(f"     TVA Rate: {article.get('tva_rate') or 'N/A'}{'%' if article.get('tva_rate') else ''}\n\n")
                else:
                    f.write("  No articles found\n\n")
            
            f.write(f"\nSource File: {pdf_path}\n")
            f.write(f"Extraction Date: {format_extraction_date()}\n")
            
            f.write(f"\nRaw AI Response:\n{json.dumps(ai_results, indent=2)}\n")
        
        print(f"\n✅ Success! Full text saved to: {output_file}")
        print(f"🤖 Gemini AI analysis saved to: {invoice_file}")
        print(f"Total characters extracted: {len(extracted_text)}")
        
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        print("Make sure the PDF file exists and is readable.")