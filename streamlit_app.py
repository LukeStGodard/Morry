import streamlit as st
import tempfile
import os
import google.genai as genai
from google.genai import types

# 1. Page Configuration for Mobile Scannability
st.set_page_config(page_title="RMCE Operations Auditor", layout="centered")
st.title("🍽️ Welcome to Morry")
st.subheader("A RM PartyPack AI Analyzer")

# 2. Hardcoded Source of Truth (Your Knowledge Base Rules)
COFFEE_SOP = """
COFFEE STATION MASTER STANDARD OPERATING PROCEDURE:
1. Grab an 8ft Table.
2. Set up the table in the desired location and put the linen on.
3. Locate Grey bins (Ask KM).
4. Bring the Urn to where coffee is being brewed or leave it in grey bin for BOH.
5. Grab the tin name cards, the stand, and the silver tray and bring them to the table.
6. Locate sugar and white bowls (Ask KM if unsure).
7. Fill up one white bowl with 3-4 packets of each sugar along the sides and fill the rest with cube sugar.
8. Grab a silver tray and a full rack of coffee cups, put them into a ring, and put 25 coffee plates in the center.
9. Grab creamer from Big Brown and pour them into the pourers.
10. Use the ceramic spoon holder and place 15-25 spoons in the holder.

BREAKDOWN PROCEDURE:
1. Grab the urns (Caution: hot), dump them in the sink or drain outside depending on venue.
2. Return sugar packets to bag/box; dump the cubes.
3. Bring remaining saucers, cups, and spoons to breakdown.
4. Put name cards, stands, and urns back into the grey bin to be washed at the Comm.
5. Put linen in the bag and return table to its original location.
"""

# 3. Securely pull your Gemini API Key from Streamlit's environment settings
if "GEMINI_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Missing Gemini API Key. Please configure it in Streamlit Secrets.")
    st.stop()

# 4. The User Interface Elements
uploaded_file = st.file_uploader("Upload Event Party Pack (PDF)", type=["pdf"])
role = st.selectbox("What is your role for this shift?", ["Select Role", "Server", "Bartender", "DRC"])

# 5. Core Processing Engine
if uploaded_file is not None and role != "Select Role":
    if st.button("Run Shift Audit"):
        with st.spinner("Analyzing Party Pack against RMCE Standards..."):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                temp_pdf.write(uploaded_file.getvalue())
                temp_path = temp_pdf.name

            try:
                # 1. Upload PDF
                img_file = client.files.upload(file=temp_path)
                api_contents = [img_file]
                visual_instructions = ""
                role_specific_sop = ""
                coffee_img_path = "Coffee_Station_SOP.jpg"
                
                # 2. Dynamic Visual SOP & Enhanced Prompt Logic
                if role in ["Server", "DRC"]:
                    role_specific_sop = f"""
                    ***SERVER & DRC SPECIFIC EXTRACTION RULES:***
                    - DO NOT include general beverage/product inventory counts or ice logistics. Focus ONLY on the following sections:
                    
                    1. ⏱️ TIMELINE: Provide a clean, chronological timeline of the shift.
                    2. 🪑 SET UP & LINENS: 
                       - List exactly how many tables and what sizes are being set up.
                       - Specify the exact linens going to those tables.
                       - **CRITICAL:** Explicitly state if the linens are RENTED or RMCE in-house.
                       - Add this exact note at the bottom of this section: "📍 *Please refer to the floor plan for exact table and station placement.*"
                    3. 🍽️ FOOD MENU: Clearly break down what the Hors d'oeuvres are and what the Dinner service consists of.
                    4. ☕ COFFEE STATION: If the packet dictates a Coffee Station, blend the logistical details from the packet with this Master SOP:
                    {COFFEE_SOP}
                    """
                        
                    if os.path.exists(coffee_img_path):
                        coffee_visual = client.files.upload(file=coffee_img_path)
                        api_contents.append(coffee_visual)
                        visual_instructions = """
                        - VISUAL SOP CROSS-CHECK: You have been provided an image reference of a pristine coffee station setup. Cross-reference the timeline and item counts in the Party Pack with this layout blueprint to verify equipment alignment.
                        """
                
                # 3. Construct System Prompt
                system_instruction = f"""
                You are an Elite Russell Morin Event Operations Agent. 
                Analyze the provided Party Pack PDF and provide role-specific logistics for the role: {role}.
                
                CRITICAL INSTRUCTIONS:
                - NO PARAGRAPHS. Use clean bullet points and Markdown tables.
                - Use emojis for headers to maintain mobile scannability.
                - Keep descriptions highly brief.
                
                {role_specific_sop}
                {visual_instructions}
                
                IF THE ROLE IS BARTENDER:
                - 📦 PRODUCT INVENTORY COUNT: Look for all beverage, food, or operational inventory line items and create a clean Markdown table displaying the item name and exact quantity provided.
                - ❄️ ICE LOGISTICS: Audit the pack to confirm if the ice requirements dictate "Bagged Ice" or "Ice in a Caddy". Explicitly state the container type and location specified.
                - Focus heavily on bar setups, specific glass counts, liquor/beer/wine inventory, bar placement timelines, and ice availability.
                - DO NOT include or mention the Coffee Station or Food Menu under any circumstances.
                """
                
                api_contents.append(f"Generate the concise operational breakdown for a {role}.")
                
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=api_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2
                    )
                )
                
                st.success("Audit Complete!")
                
                # 4. Render the physical image FIRST
                if role in ["Server", "DRC"] and "COFFEE STATION" in response.text.upper():
                    if os.path.exists(coffee_img_path):
                        st.image(coffee_img_path, caption="Visual Reference: Pristine Coffee Station Layout", use_container_width=True)
                
                # 5. Render the text UNDERNEATH the image
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"An operational error occurred during data analysis: {e}")
