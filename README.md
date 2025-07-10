# PDF Invoice Data Extractor with Gemini AI

🤖 An intelligent PDF invoice analyzer that extracts structured data using Google's Gemini AI.

## Features

- **PDF Text Extraction**: Converts PDF invoices to text using pdfminer
- **AI-Powered Analysis**: Uses Google Gemini AI to intelligently extract invoice data
- **Comprehensive Data Extraction**:
  - Invoice number, dates, amounts (TTC, HT, TVA)
  - Company information (name, address, phone, email, ICE)
  - Client information
  - Bank details (IBAN, RIB)
  - Detailed articles/items with quantities and prices
- **Multilingual Support**: Available in English and French
- **Structured Output**: JSON format with organized data
- **File Organization**: Automatic saving to organized folders

## Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/invoice-pdf-extractor.git
cd invoice-pdf-extractor
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up your Google AI API key**:
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Set it as an environment variable (recommended):
     ```bash
     export GOOGLE_API_KEY="your_api_key_here"
     ```
   - Or edit the script to use your hardcoded key (for testing only)

## Usage

### English Version
```bash
python test_ai.py "path/to/your/invoice.pdf"
```

### French Version
```bash
python test_ai_fr.py "path/to/your/invoice.pdf"
```

### Example Output
```
🤖 ANALYSE DE FACTURE POWERED BY GEMINI AI
============================================================
📄 Numéro de Facture: FAC-2024-001
📅 Date de Facturation: 15/03/2024
💰 Total TTC: 3,876 €
💵 Total HT: 3,230 €
🧾 Montant TVA: 646 €

🏢 INFORMATIONS ENTREPRISE:
  Nom: SARL EXEMPLE SERVICES
  Adresse: 123 Rue de la République, 75001 Paris
  Téléphone: +33 1 42 36 78 90
  Email: contact@exemple-services.com

🛒 ARTICLES:
  1. Service de consultation IT
     Quantité: 5
     Prix Unitaire: 450 €
     Prix Total: 2,250 €
     Taux TVA: 20%
```

## File Structure

```
project/
├── test_ai.py              # English version
├── test_ai_fr.py           # French version (Version française)
├── test.py                 # Classic regex-based extraction
├── analysis/               # AI analysis results
├── text save/             # Extracted PDF text
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## API Key Setup

### Option 1: Environment Variable (Recommended)
```bash
# Linux/Mac
export GOOGLE_API_KEY="your_api_key_here"

# Windows
set GOOGLE_API_KEY=your_api_key_here
```

### Option 2: Direct in Code (Testing Only)
Edit the script and replace the API key in the `ai_extract_invoice_data` function.

## Dependencies

- `pdfminer.six`: PDF text extraction
- `google-generativeai`: Google Gemini AI API
- `re`, `json`, `os`, `sys`: Standard Python libraries

## Supported Invoice Formats

The AI can extract data from various invoice formats including:
- French invoices (factures)
- Multi-language invoices
- Different layouts and structures
- Various currencies (€, $, etc.)

## Output Files

The script automatically creates:
- **Extracted text**: `text save/{filename}_extracted.txt`
- **AI analysis**: `analysis/{filename}_gemini_analysis.txt` (English) or `analysis/{filename}_gemini_analysis_fr.txt` (French)

## Troubleshooting

### Common Issues

1. **"API key not valid"**: 
   - Ensure your API key is correct
   - Check that Generative AI API is enabled in Google Cloud Console
   - Verify billing is set up (required for Gemini API)

2. **"No suitable model found"**:
   - Check your internet connection
   - Verify API key permissions

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Note**: Keep your API keys secure and never commit them to public repositories!
