import streamlit as st
import google.generative_ai as genai
import matplotlib.pyplot as plt
import io
import pandas as pd
import xlsxwriter

# ==========================================
# 1. 核心大脑配置 (车间铁律)
# ==========================================
SHOP_RULES = """
# Role
You are a Senior Manufacturing Engineer. Generate Python code using `matplotlib` to render HVAC ductwork drawings.

# Critical Shop Floor Rules
1. **Elbows:** Radius R = 1.5 * Diameter. Must include 50mm straight tangents at both ends.
2. **Reducers:** Length L is typically 300mm. If (D1-D2)>200, L=500. Include 50mm straight tangents.
3. **General:** Use `mm` for all units.

# Python Code Constraints
1. Use `fig, ax = plt.subplots(figsize=(8, 6))`
2. Draw the shape using `patches.Polygon` or `patches.Arc`.
3. Add clear annotations for Dimensions (Ø, L, R, Angle).
4. **IMPORTANT:** DO NOT use `plt.show()`. DO NOT save to file with `savefig`.
5. The final plot object must be stored in a variable named `fig`.
6. Output raw Python code only. No markdown formatting (no ```python).
"""

# ==========================================
# 2. 页面布局与设置
# ==========================================
st.set_page_config(page_title="Acesian Auto-Drafter", page_icon="🏭", layout="wide")

# 侧边栏：控制台
with st.sidebar:
    st.title("🏭 Acesian Tech")
    st.markdown("---")
    
    # API Key 输入区 (密码模式)
    api_key = st.text_input("🔑 输入 Google API Key:", type="password", help="去 Google AI Studio 获取")
    
    st.markdown("---")
    st.info("💡 操作指南:\n1. 输入 API Key\n2. 选择零件类型\n3. 填入尺寸\n4. 点击生成")

# 主界面
st.header("HVAC 自动化绘图系统 (Web版)")

# 左右分栏布局
col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("1. 参数设定")
    # 下拉菜单
    comp_type = st.selectbox(
        "选择零件类型", 
        ["Elbow (弯头)", "Reducer (变径)", "Straight (直管)", "Tee (三通)"]
    )
    
    # 动态输入框
    params = {}
    if "Elbow" in comp_type:
        col_a, col_b = st.columns(2)
        params['d1'] = col_a.number_input("直径 D1 (mm)", value=500, step=50)
        params['angle'] = col_b.number_input("角度 (°)", value=90, step=15)
    
    elif "Reducer" in comp_type:
        col_a, col_b = st.columns(2)
        params['d1'] = col_a.number_input("大头 D1 (mm)", value=500, step=50)
        params['d2'] = col_b.number_input("小头 D2 (mm)", value=300, step=50)
        params['length'] = st.number_input("长度 L (mm)", value=300, step=50)
        
    elif "Straight" in comp_type:
        col_a, col_b = st.columns(2)
        params['d1'] = col_a.number_input("直径 D (mm)", value=300, step=50)
        params['length'] = col_b.number_input("长度 L (mm)", value=1200, step=100)
        
    elif "Tee" in comp_type:
        col_a, col_b = st.columns(2)
        params['main_d'] = col_a.number_input("主管直径 (mm)", value=500, step=50)
        params['tap_d'] = col_b.number_input("支管直径 (mm)", value=300, step=50)

    # 生成按钮
    generate_btn = st.button("🚀 开始绘图", type="primary", use_container_width=True)

# ==========================================
# 3. 核心处理逻辑
# ==========================================
if generate_btn:
    if not api_key:
        st.error("❌ 请先在左侧输入 Google API Key！")
        st.stop()

    with col2:
        st.subheader("2. 图纸预览")
        status_container = st.empty()
        status_container.info("⏳ 正在呼叫 AI 工程师绘图...")

        try:
            # 1. 配置 AI
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=SHOP_RULES)
            
            # 2. 发送指令
            user_prompt = f"Draw a {comp_type} with these parameters: {params}."
            response = model.generate_content(user_prompt)
            
            # 3. 清理代码
            code = response.text
            code = code.replace("```python", "").replace("```", "").strip()
            
            # 4. 执行代码 (Safe Execution Environment)
            local_vars = {}
            exec(code, globals(), local_vars)
            
            # 5. 获取结果
            if 'fig' in local_vars:
                fig = local_vars['fig']
                status_container.success("✅ 绘图完成！")
                
                # 显示图片
                st.pyplot(fig)
                
                # 6. 生成 Excel 下载
                img_buf = io.BytesIO()
                fig.savefig(img_buf, format='png', bbox_inches='tight', dpi=100)
                img_buf.seek(0)
                
                excel_buf = io.BytesIO()
                with pd.ExcelWriter(excel_buf, engine='xlsxwriter') as writer:
                    df = pd.DataFrame([
                        {"Item": comp_type, "Params": str(params), "Qty": 1, "Notes": "Auto-generated"}
                    ])
                    df.to_excel(writer, sheet_name='Order', index=False)
                    worksheet = writer.sheets['Order']
                    worksheet.set_column('C:C', 40)
                    worksheet.set_row(1, 150)
                    worksheet.insert_image('C2', 'sketch.png', {'image_data': img_buf, 'x_scale': 0.6, 'y_scale': 0.6})
                
                # 下载按钮
                st.download_button(
                    label="📥 下载 Excel 生产单",
                    data=excel_buf.getvalue(),
                    file_name="acesian_order.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                status_container.error("⚠️ AI 生成了代码，但没有生成 fig 变量。请重试。")
                with st.expander("查看调试代码"):
                    st.code(code)

        except Exception as e:
            status_container.error(f"❌ 发生错误: {str(e)}")
            st.warning("提示: 检查 API Key 是否正确，或尝试刷新页面。")