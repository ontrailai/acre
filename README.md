# Lease Logik 2

Lease Logik 2 (LL2) is an AI-native lease abstraction and document intelligence platform designed to eliminate the need for human paralegals, analysts, and junior staff to read, extract, summarize, and risk-assess commercial real estate leases.

## 🧠 Features

- **One-Step Lease Abstraction**: Upload a lease PDF and get a complete summary in seconds
- **GPT-4-Turbo Intelligence**: Advanced LLM that reads like a legal mind, extracts key clauses, and identifies risks
- **Deep Traceability**: Every extracted clause links back to the source text and page number
- **Risk Detection**: Automatically flags potentially problematic clauses with severity levels
- **Structured Data + Summary**: Clean bullet-point abstracts and structured JSON data
- **Flexible Exports**: Download results as PDF, Word, Excel, or raw Markdown
- **Self-Learning System**: Improves with every lease processed and every feedback received
- **Clean, Simple UX**: Drop a lease PDF → Get a summary. No complex workflow

## 🛠️ Enhanced Technology 

### Backend Intelligence
- **Section-Specific GPT Prompting**: Specialized prompts for different lease sections (rent, assignment, insurance, etc.)
- **Deep Legal Reading**: GPT not just as a data extractor but as a legal analyst that understands intent
- **Advanced Risk Detection**: Identifies issues like broad assignment rights, termination clauses, undefined rent escalations
- **Structured Extraction**: All GPT responses include structured data, human-readable summaries, risk flags, and source excerpts
- **Confidence Scoring**: Every extracted clause includes a confidence rating to flag potential errors

### Enhanced UX Flow
- **True One-Click Process**: Single API endpoint that handles upload→OCR→segment→extract→summarize→export
- **Hover-Over Traceability**: Interactive UI that shows source text when hovering over clauses
- **Structured Feedback System**: Field-specific feedback collection for targeted retraining
- **Risk Categorization**: Risks displayed by severity (high/medium/low) with clear explanations
- **Processing Stage Visibility**: Clear indication of what's happening behind the scenes

## 🖥️ Tech Stack

### Backend
- FastAPI (Python)
- OpenAI GPT-4-Turbo
- PyMuPDF + Tesseract OCR
- Markdown, ReportLab, python-docx, XlsxWriter for exports

### Frontend
- React with Vite
- Tailwind CSS
- React Dropzone for file uploads
- React Markdown for summary rendering

## 📋 Getting Started

### Prerequisites
- Python 3.9+
- Node.js 16+
- OpenAI API Key

### Backend Setup
```bash
cd backend
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=your_key_here

# Run the server
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173 to access the application.

## 💻 Usage

1. Select the lease type (Retail, Office, or Industrial)
2. Choose the summary style (Executive Brief or Legal Detail)
3. Drop your lease PDF file into the dropzone
4. Watch as the system processes your document with real-time status updates
5. View the structured summary with risk flags and source traceability
6. Export to your preferred format or provide feedback to improve the system

## 🔄 Intelligent Workflow

1. **Upload**: PDF is saved and processed (native or scanned)
2. **OCR**: If needed, text is extracted with Tesseract OCR
3. **Segmentation**: Lease is divided into logical sections using pattern recognition
4. **GPT Extraction**: Each section is analyzed by GPT-4-Turbo with section-specific prompts
5. **Risk Analysis**: Specialized algorithms identify potential legal and business risks
6. **Summary Generation**: A clean, bullet-point abstract is created with traceability to source text
7. **Feedback Collection**: User corrections are stored with precise field IDs for future training

## 🧪 Self-Learning System

The system gets smarter with every lease through:

1. **Structured Feedback**: Each correction is stored with its exact field ID
2. **Field-Specific Training**: Corrections are grouped by clause type for targeted improvements
3. **Cross-Lease Learning**: Similar clauses across different leases help build a broader understanding
4. **Confidence Tracking**: The system monitors which clauses it struggles with most

## 🚀 Key Improvements

- **True one-step user experience** - no separate extraction button
- **Section-specific GPT prompting** for better legal analysis
- **Deep risk detection** that spans multiple clause types
- **Interactive traceability** between summary and source text
- **Structured feedback collection** for targeted model improvement
- **Detailed processing stages** to give users visibility into the process

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
