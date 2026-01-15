import streamlit as st
import requests
import re
import json
import pandas as pd

st.set_page_config(page_title="UPS Comparison Tool", page_icon="🔌", layout="wide")

def extract_specs(content):
    """Extract specifications using multiple regex patterns"""
    result = {
        'product_id': 'Not found',
        'power_w': 'Not found',
        'power_va': 'Not found',
        'ups_type': 'Not found',
        'wave_type': 'Not found',
        'output_connection': 'Not found',
        'colour': 'Not found',
        'height': 'Not found',
        'width': 'Not found',
        'depth': 'Not found'
    }
    
    # Extract product ID first
    product_id_pattern = r'"productId"\s*:\s*"([^"]+)"'
    product_id_match = re.search(product_id_pattern, content)
    if product_id_match:
        result['product_id'] = product_id_match.group(1)
    
    # Method 1: Direct JSON parsing if possible
    try:
        spec_match = re.search(r'specifications:\s*(\{[^}]*characteristicTables[^}]*\[[^\]]*\].*?\})\s*(?:,|\}|$)', content, re.DOTALL)
        if not spec_match:
            spec_match = re.search(r'specifications:\s*(\{.*?\})\s*(?:[,\}]|$)', content, re.DOTALL)
        
        if spec_match:
            json_str = spec_match.group(1)
            json_str_fixed = re.sub(r'(\w+):', r'"\1":', json_str)
            
            try:
                data = json.loads(json_str_fixed)
                
                for table in data.get('characteristicTables', []):
                    for row in table.get('rows', []):
                        char_name = row.get('characteristicName', '')
                        values = row.get('characteristicValues', [])
                        
                        if values:
                            label_text = values[0].get('labelText', 'Not found')
                            
                            if 'Maximum configurable power in W' in char_name:
                                result['power_w'] = label_text
                            elif 'Maximum configurable power in VA' in char_name:
                                result['power_va'] = label_text
                            elif 'UPS type' in char_name:
                                result['ups_type'] = label_text
                            elif 'Wave type' in char_name:
                                result['wave_type'] = label_text
                            elif 'Output connection type' in char_name:
                                result['output_connection'] = label_text
                            elif 'Colour' in char_name:
                                result['colour'] = label_text
                            elif 'Height' in char_name:
                                result['height'] = label_text
                            elif 'Width' in char_name:
                                result['width'] = label_text
                            elif 'Depth' in char_name:
                                result['depth'] = label_text
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    
    # Method 2: Regex patterns for embedded data
    specs_to_extract = {
        'power_w': ['Maximum configurable power in W'],
        'power_va': ['Maximum configurable power in VA'],
        'ups_type': ['UPS type'],
        'wave_type': ['Wave type'],
        'output_connection': ['Output connection type'],
        'colour': ['Colour', 'Color'],
        'height': ['Height'],
        'width': ['Width'],
        'depth': ['Depth']
    }
    
    for key, names in specs_to_extract.items():
        if result[key] == 'Not found':
            for name in names:
                patterns = [
                    rf'characteristicName["\s:]+{name}["\s,}}]+.*?labelText["\s:]+([^"]+)"',
                    rf'"{name}".*?labelText["\s:]+([^"]+)"',
                ]
                for pattern in patterns:
                    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                    if match:
                        result[key] = match.group(1).strip().replace('\\u003Cbr />', ', ')
                        break
                if result[key] != 'Not found':
                    break
    
    return result

# Streamlit UI
st.title("🔌 UPS Comparison Tool")
st.markdown("Compare up to 6 UPS products side-by-side")

# Create input fields for URLs
st.subheader("Enter Product URLs")
urls = []
for i in range(1, 7):
    url = st.text_input(f"Product {i} URL:", key=f"url_{i}", placeholder=f"https://example.com/product-{i}")
    if url.strip():
        urls.append(url.strip())

# Generate comparison button
if st.button("🔍 Generate Comparison Table", type="primary", use_container_width=True):
    if not urls:
        st.error("Please enter at least one URL")
    else:
        results = []
        errors = []
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        for idx, url in enumerate(urls):
            try:
                status_text.text(f"Fetching product {idx + 1} of {len(urls)}...")
                progress_bar.progress((idx + 1) / len(urls))
                
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                specs = extract_specs(response.text)
                results.append(specs)
                
            except requests.exceptions.RequestException as e:
                errors.append(f"Error fetching URL {idx + 1}: {str(e)}")
            except Exception as e:
                errors.append(f"Error processing URL {idx + 1}: {str(e)}")
        
        progress_bar.empty()
        status_text.empty()
        
        # Display errors if any
        if errors:
            for error in errors:
                st.error(error)
        
        # Display results
        if results:
            st.success(f"✅ Successfully extracted data from {len(results)} product(s)!")
            
            # Create DataFrame for comparison
            spec_labels = {
                'product_id': 'Product ID',
                'power_w': 'Maximum Power (W)',
                'power_va': 'Maximum Power (VA)',
                'ups_type': 'UPS Type',
                'wave_type': 'Wave Type',
                'output_connection': 'Output Connection',
                'colour': 'Colour',
                'height': 'Height',
                'width': 'Width',
                'depth': 'Depth'
            }
            
            # Build comparison table
            comparison_data = {}
            for idx, result in enumerate(results):
                product_name = result['product_id'] if result['product_id'] != 'Not found' else f"Product {idx + 1}"
                comparison_data[product_name] = [result[key] for key in spec_labels.keys()]
            
            df = pd.DataFrame(comparison_data, index=spec_labels.values())
            
            # Display as a styled table
            st.dataframe(
                df,
                use_container_width=True,
                height=400
            )
            
            # Download option
            csv = df.to_csv()
            st.download_button(
                label="📥 Download Comparison as CSV",
                data=csv,
                file_name="ups_comparison.csv",
                mime="text/csv",
                use_container_width=True
            )

# Add footer
st.markdown("---")
st.markdown("💡 **Tip:** You can enter between 1 and 6 product URLs for comparison")