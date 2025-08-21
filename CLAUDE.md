# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a print farm label generation system with two main components:

1. **print-brain** - Python Flask backend that generates PDF labels and prints them
   - Flask API server with CORS support
   - Uses ReportLab for PDF generation
   - Creates landscape-oriented labels with bold text that fills the available space
   - Supports three label sizes:
     - 3" x 1" (Small Green labels)
     - 102mm x 51mm (Medium White labels)
     - 4" x 6.25" (Large Shipping labels)
   - Windows printing support via pywin32 (prints to default printer)
   - All label sizes can be printed
   - Files saved to OUTPUT_DIR (default: C:\labels on Windows)

2. **print-farm-frontend** - SvelteKit web application  
   - SvelteKit 2 with Svelte 5, TypeScript, and Tailwind CSS
   - Drizzle ORM with PostgreSQL (Neon serverless)
   - API proxy endpoint at `/api/labels/generate` that forwards requests to print-brain instances
   - Supports routing to multiple printer targets (small/medium/large) with configurable URLs via environment variables

## Development Commands

### Frontend (print-farm-frontend)

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run check

# Linting and formatting
npm run lint
npm run format

# Run tests
npm run test:unit
npm run test:e2e
npm run test

# Database operations (requires DATABASE_URL env var)
npm run db:push     # Push schema changes
npm run db:generate # Generate migrations
npm run db:migrate  # Run migrations
npm run db:studio   # Open Drizzle Studio
```

### Backend (print-brain)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py

# Environment variables
PORT=3001            # Server port (default: 3001)
OUTPUT_DIR=C:\labels # PDF output directory
LABEL_SIZE=3x1       # Default label size (3x1, 102x51mm, 4x6.25)
```

## Environment Configuration

### Frontend Environment Variables

- `DATABASE_URL` - PostgreSQL connection string (required for Drizzle)
- `PRINTER_SMALL_URL` - URL for small green 3x1 printer (default: http://100.105.161.92:3001)
- `PRINTER_MEDIUM_URL` - URL for medium white 102x51mm printer (default: http://100.105.161.92:3002)
- `PRINTER_LARGE_URL` - URL for large shipping 4x6.25 printer (default: http://100.105.161.92:3003)

## API Endpoints

### print-brain (Python Backend)
- `GET /` - Health check, service info, and printer status
- `GET /printer` - Get default printer information
- `POST /generate` - Generate PDF label with optional printing (print: true/false)
- `GET /files/<filename>` - Download generated PDF

### Frontend API
- `GET /api/labels` - API info
- `POST /api/labels/generate` - Proxy to remote print-brain service (supports print parameter)

## Key Implementation Details

- The frontend proxies label generation requests to configurable print-brain instances based on the target printer size
- PDF generation creates landscape-oriented labels with text sized to maximize use of available space
- The system supports dry run mode to test without calling remote services
- Generated PDFs are stored locally on the print-brain server and can be retrieved via the /files endpoint
- Windows printing is supported via pywin32, using the system's default printer
- All label sizes (3x1, 102x51mm, 4x6.25) can be printed
- The print parameter in API requests triggers automatic printing after PDF generation
- Printer mapping:
  - Small printer (100.105.161.92:3001) → 3" x 1" green labels
  - Medium printer (100.105.161.92:3002) → 102mm x 51mm white labels
  - Large printer (100.105.161.92:3003) → 4" x 6.25" shipping labels