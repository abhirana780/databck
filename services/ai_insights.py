import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq Client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def generate_insights(data):
    """
    Analyzes sales data and generates insights using Groq LLM.
    """
    try:
        if not data:
            return "No sales data available for analysis."

        # Summarize data for the prompt
        total_sales = sum(item.get('sales_amount', 0) for item in data)
        total_profit = sum(item.get('profit', 0) for item in data)
        top_product = max(data, key=lambda x: x.get('sales_amount', 0)).get('product_name', 'N/A') if data else 'N/A'
        
        # Simple trend analysis (based on last few items vs first few in the sample)
        # Note: data is assumed to be the last 100 records
        
        prompt = f"""
        You are a business intelligence AI. 
        Analyze the following sales summary and generate structured business insights.
        
        DATA SUMMARY:
        - Total Records Analyzed: {len(data)}
        - Aggregate Sales Amount: ₹{total_sales:,.2f}
        - Aggregate Profit: ₹{total_profit:,.2f}
        - Top Performing Product: {top_product}
        
        RAW DATA SAMPLE (Last few records):
        {data[:10]}
        
        Please provide your response in the following structured sections:
        ### 📈 Key Trends
        ### 🏆 Top Performing Products & Regions
        ### 👥 Customer Insights
        ### ⚠️ Anomalies & Alerts
        ### 💡 Strategic Suggestions for Growth
        
        Keep it professional, data-driven, and concise.
        """

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
        )

        return chat_completion.choices[0].message.content

    except Exception as e:
        print(f"Groq API Error: {e}")
        return f"Error generating insights: {str(e)}"

def ask_ai_question(question, data):
    """
    Handles custom user questions about the data.
    """
    try:
        total_sales = sum(item.get('sales_amount', 0) for item in data)
        
        prompt = f"""
        You are a business intelligence AI. Use the provided context to answer the user's question.
        
        CONTEXT:
        - Total Sales: ₹{total_sales:,.2f}
        - Records Analyzed: {len(data)}
        - Data Sample: {data[:20]}
        
        USER QUESTION: {question}
        
        Answer professionally based ONLY on the data provided.
        """

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"
