# VaultMind Logo Integration Setup

## Quick Setup Instructions

### Step 1: Save Your Logo
1. Save your VaultMind logo image as `vaultmind_logo.png` in the `assets/` folder
2. Recommended size: 240x120 pixels (2:1 ratio) for best display
3. Format: PNG with transparent background preferred

### Step 2: File Location
```
genai-knowledge-assistant/
├── assets/
│   └── vaultmind_logo.png  ← Your logo goes here
├── utils/
│   └── logo_handler.py     ← Already created
└── genai_dashboard.py      ← Already updated
```

### Step 3: Test the Integration
1. Run your Streamlit dashboard: `streamlit run genai_dashboard.py`
2. Your VaultMind logo should appear in the top-right corner
3. If the logo file is not found, a green fallback logo will display

## Logo Specifications

### Current Fallback Design
- **Background**: Green (#22c55e) - matching your brand
- **Icons**: 🔒🧠 (lock + brain)
- **Text**: "VaultMind" + "AI Assistant"
- **Position**: Fixed top-right corner
- **Size**: 120px width, auto height

### Recommended Logo Design
- **Dimensions**: 240x120px or 120x60px
- **Format**: PNG with transparent background
- **Colors**: Your brand green (#22c55e) with white text
- **Content**: Brain-lock icon + "VaultMind" text

## Customization Options

### Change Logo Size
Edit the CSS in `genai_dashboard.py`:
```css
.vaultmind-logo {
    width: 150px;  /* Change this value */
}
```

### Change Logo Position
```css
.vaultmind-logo {
    top: 10px;     /* Distance from top */
    right: 10px;   /* Distance from right */
}
```

### Use Different Logo File
Update the path in the logo handler call:
```python
display_vaultmind_logo("assets/my_custom_logo.png")
```

## Troubleshooting

### Logo Not Showing
1. Check file path: `assets/vaultmind_logo.png`
2. Verify file permissions
3. Check browser console for errors
4. Refresh the Streamlit app

### Logo Too Large/Small
1. Resize the image file, or
2. Adjust CSS width property
3. Maintain aspect ratio for best results

## Next Steps
Once your logo is displaying correctly, you're ready to proceed with the production deployment planning!
