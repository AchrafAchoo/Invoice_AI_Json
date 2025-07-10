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
    print("Vérification des modèles Gemini disponibles...")
    
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
        
        print(f"Trouvé {len(available_models)} modèles compatibles")
        
        for preferred in preferred_models:
            if preferred in available_models:
                print(f"Modèle préféré sélectionné: {preferred}")
                return preferred
        
        if available_models:
            selected = available_models[0]
            print(f"Utilisation du premier modèle disponible: {selected}")
            return selected
            
        print("Aucun modèle Gemini compatible avec 'generateContent' trouvé.")
        return None
        
    except Exception as e:
        print(f"Erreur lors de la liste des modèles Gemini: {e}")
        return None

def ai_extract_invoice_data(text):
    
    try:
        api_key = os.environ.get("GOOGLE_API_KEY") 
        if not api_key:
            # Replace 'your_api_key_here' with your actual API key for testing
            api_key = "your_api_key_here"
            print("Attention: Utilisation d'une clé API en dur. Considérez définir la variable d'environnement GOOGLE_API_KEY pour la production.")

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
                "company_info": {"name": None, "address": None, "phone": None, "email": None, "ICE": None},
                "client_info": {"name": None, "address": None},
                "bank_info": {"bank_name": None, "iban": None, "rib": None},
                "articles": [],
                "error": "Aucun modèle Gemini approprié trouvé pour effectuer l'extraction."
            }
        
        model = genai.GenerativeModel(model_name)

        prompt = f"""
        Analysez ce texte de facture et extrayez TOUTES les informations suivantes. Soyez très attentif et précis:

        1. Numéro de facture
        2. Date de facturation
        3. Date d'échéance
        4. Total TTC (montant final incluant les taxes)
        5. Montant TVA/VAT
        6. Sous-total HT (montant avant taxes)
        7. Informations de l'entreprise/vendeur (nom, adresse, téléphone, email, ICE, etc.)
        8. Informations du client/acheteur (nom, adresse)
        9. Informations bancaires (nom de la banque, IBAN, RIB si présent)
        10. Articles/produits achetés avec détails (description, quantité, prix unitaire, prix total, taux TVA)

        Retournez le résultat dans ce format JSON exact:
        {{
            "invoice_number": "numéro trouvé ou null",
            "billing_date": "date ou null",
            "due_date": "date ou null",
            "total_ttc": "montant sans symbole monétaire ou null",
            "total_ht": "montant sans symbole monétaire ou null", 
            "tva_amount": "montant sans symbole monétaire ou null",
            "company_info": {{
                "name": "nom de l'entreprise ou null",
                "address": "adresse complète ou null",
                "phone": "numéro de téléphone ou null",
                "email": "email ou null",
                "ICE": "numéro ICE ou null"
            }},
            "client_info": {{
                "name": "nom du client ou null",
                "address": "adresse du client ou null"
            }},
            "bank_info": {{
                "bank_name": "nom de la banque ou null",
                "iban": "IBAN ou null",
                "rib": "RIB ou null"
            }},
            "articles": [
                {{
                    "description": "description de l'article",
                    "quantity": "quantité ou null",
                    "unit_price": "prix unitaire ou null",
                    "total_price": "prix total ou null",
                    "tva_rate": "pourcentage TVA ou null"
                }}
            ]
        }}

        Texte de la facture:
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
                "error": f"Échec de l'analyse de la réponse AI. Réponse brute: {result[:200]}..."
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
            "error": f"Échec de l'extraction AI: {str(e)}"
        }

def format_extraction_date():
    return datetime(2025, 7, 10).strftime("%d/%m/%Y")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Utilisation: python test_ai_french.py <nom_fichier_pdf>")
        print("Exemple: python test_ai_french.py modele_de_facture.pdf")
        print("Pour les fichiers avec espaces: python test_ai_french.py \"fichier avec espaces.pdf\"")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"❌ Erreur: Fichier '{pdf_path}' introuvable!")
        print("Assurez-vous que le fichier existe dans le répertoire courant.")
        print("Pour les fichiers avec espaces dans le nom, utilisez des guillemets autour du nom de fichier.")
        sys.exit(1)
    
    try:
        print("Début de la conversion PDF vers texte...")
        print(f"Traitement du fichier: {pdf_path}")
        
        extracted_text = convert_pdf_to_txt(pdf_path)
        
        print("\n🤖 Utilisation de Gemini AI pour analyser la facture...")
        ai_results = ai_extract_invoice_data(extracted_text)
        
        print("\n" + "="*60)
        print("🤖 ANALYSE DE FACTURE POWERED BY GEMINI AI")
        print("="*60)
        
        if ai_results.get("error"):
            print(f"❌ Erreur AI: {ai_results['error']}")
        else:
            print("-" * 60)
            
            print(f"📄 Numéro de Facture: {ai_results.get('invoice_number') or 'Non trouvé'}")
            print(f"📅 Date de Facturation: {ai_results.get('billing_date') or 'Non trouvé'}")
            print(f"⏰ Date d'Échéance: {ai_results.get('due_date') or 'Non trouvé'}")
            print(f"💰 Total TTC: {ai_results.get('total_ttc') or 'Non trouvé'} {'€' if ai_results.get('total_ttc') else ''}")
            print(f"💵 Total HT: {ai_results.get('total_ht') or 'Non trouvé'} {'€' if ai_results.get('total_ht') else ''}")
            print(f"🧾 Montant TVA: {ai_results.get('tva_amount') or 'Non trouvé'} {'€' if ai_results.get('tva_amount') else ''}")
            
            print(f"\n🏢 INFORMATIONS ENTREPRISE:")
            company = ai_results.get('company_info', {})
            print(f"  Nom: {company.get('name') or 'Non trouvé'}")
            print(f"  Adresse: {company.get('address') or 'Non trouvé'}")
            print(f"  Téléphone: {company.get('phone') or 'Non trouvé'}")
            print(f"  Email: {company.get('email') or 'Non trouvé'}")
            print(f"  ICE: {company.get('ICE') or 'Non trouvé'}")
            
            print(f"\n👤 INFORMATIONS CLIENT:")
            client = ai_results.get('client_info', {})
            print(f"  Nom: {client.get('name') or 'Non trouvé'}")
            print(f"  Adresse: {client.get('address') or 'Non trouvé'}")
            
            print(f"\n🏦 INFORMATIONS BANCAIRES:")
            bank = ai_results.get('bank_info', {})
            print(f"  Nom de la Banque: {bank.get('bank_name') or 'Non trouvé'}")
            print(f"  IBAN: {bank.get('iban') or 'Non trouvé'}")
            print(f"  RIB: {bank.get('rib') or 'Non trouvé'}")
            
            print(f"\n🛒 ARTICLES:")
            articles = ai_results.get('articles', [])
            if articles:
                for i, article in enumerate(articles, 1):
                    print(f"  {i}. {article.get('description') or 'Aucune description'}")
                    print(f"     Quantité: {article.get('quantity') or 'N/A'}")
                    print(f"     Prix Unitaire: {article.get('unit_price') or 'N/A'} {'€' if article.get('unit_price') else ''}")
                    print(f"     Prix Total: {article.get('total_price') or 'N/A'} {'€' if article.get('total_price') else ''}")
                    print(f"     Taux TVA: {article.get('tva_rate') or 'N/A'}{'%' if article.get('tva_rate') else ''}")
                    print()
            else:
                print("  Aucun article trouvé")
        
        print("="*60)
        
        print("\n--- Premiers 500 caractères du texte extrait ---")
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
        
        invoice_file = os.path.join(analysis_folder, f"{pdf_name}_gemini_analysis_fr.txt")
        with open(invoice_file, 'w', encoding='utf-8') as f:
            f.write("ANALYSE DE FACTURE POWERED BY GEMINI AI\n")
            f.write("="*40 + "\n\n")
            
            if ai_results.get("error"):
                f.write(f"ERREUR: {ai_results['error']}\n\n")
            else:
                f.write(f"Numéro de Facture: {ai_results.get('invoice_number') or 'Non trouvé'}\n")
                f.write(f"Date de Facturation: {ai_results.get('billing_date') or 'Non trouvé'}\n")
                f.write(f"Date d'Échéance: {ai_results.get('due_date') or 'Non trouvé'}\n")
                f.write(f"Total TTC: {ai_results.get('total_ttc') or 'Non trouvé'} {'€' if ai_results.get('total_ttc') else ''}\n")
                f.write(f"Total HT: {ai_results.get('total_ht') or 'Non trouvé'} {'€' if ai_results.get('total_ht') else ''}\n")
                f.write(f"Montant TVA: {ai_results.get('tva_amount') or 'Non trouvé'} {'€' if ai_results.get('tva_amount') else ''}\n\n")
                
                f.write("INFORMATIONS ENTREPRISE:\n")
                company = ai_results.get('company_info', {})
                f.write(f"  Nom: {company.get('name') or 'Non trouvé'}\n")
                f.write(f"  Adresse: {company.get('address') or 'Non trouvé'}\n")
                f.write(f"  Téléphone: {company.get('phone') or 'Non trouvé'}\n")
                f.write(f"  Email: {company.get('email') or 'Non trouvé'}\n")
                f.write(f"  ICE: {company.get('ICE') or 'Non trouvé'}\n\n")
                
                f.write("INFORMATIONS CLIENT:\n")
                client = ai_results.get('client_info', {})
                f.write(f"  Nom: {client.get('name') or 'Non trouvé'}\n")
                f.write(f"  Adresse: {client.get('address') or 'Non trouvé'}\n\n")
                
                f.write("INFORMATIONS BANCAIRES:\n")
                bank = ai_results.get('bank_info', {})
                f.write(f"  Nom de la Banque: {bank.get('bank_name') or 'Non trouvé'}\n")
                f.write(f"  IBAN: {bank.get('iban') or 'Non trouvé'}\n")
                f.write(f"  RIB: {bank.get('rib') or 'Non trouvé'}\n\n")
                
                f.write("ARTICLES:\n")
                articles = ai_results.get('articles', [])
                if articles:
                    for i, article in enumerate(articles, 1):
                        f.write(f"  {i}. {article.get('description') or 'Aucune description'}\n")
                        f.write(f"     Quantité: {article.get('quantity') or 'N/A'}\n")
                        f.write(f"     Prix Unitaire: {article.get('unit_price') or 'N/A'} {'€' if article.get('unit_price') else ''}\n")
                        f.write(f"     Prix Total: {article.get('total_price') or 'N/A'} {'€' if article.get('total_price') else ''}\n")
                        f.write(f"     Taux TVA: {article.get('tva_rate') or 'N/A'}{'%' if article.get('tva_rate') else ''}\n\n")
                else:
                    f.write("  Aucun article trouvé\n\n")
            
            f.write(f"\nFichier Source: {pdf_path}\n")
            f.write(f"Date d'Extraction: {format_extraction_date()}\n")
            
            f.write(f"\nRéponse AI Brute:\n{json.dumps(ai_results, indent=2, ensure_ascii=False)}\n")
        
        print(f"\n✅ Succès! Texte complet sauvegardé dans: {output_file}")
        print(f"🤖 Analyse Gemini AI sauvegardée dans: {invoice_file}")
        print(f"Total de caractères extraits: {len(extracted_text)}")
        
    except Exception as e:
        print(f"❌ Erreur survenue: {str(e)}")
        print("Assurez-vous que le fichier PDF existe et est lisible.")
