import streamlit as st
import matplotlib.pyplot as plt
from dos_attack_simulator import SimulationConfig, simulate

# Налаштування сторінки додатка
st.set_page_config(
    page_title="Моделювання DoS-атаки",
    page_icon="🛡️",
    layout="wide"
)

# Заголовок додатка (відповідно до теми курсової)
st.title("🛡️ Моделювання DoS-атаки на вузли мережі та аналіз її наслідків")
st.markdown("---")

# ==========================================
# БІЧНА ПАНЕЛЬ (Параметри моделювання)
# ==========================================
st.sidebar.header("⚙️ Параметри моделі")

duration_steps = st.sidebar.slider("Тривалість моделювання (кроків)", 50, 500, 240, step=10)
normal_arrival_rate = st.sidebar.slider("Штатний режим (інтенсивність λ)", 1.0, 10.0, 3.0, step=0.5)
attack_arrival_rate = st.sidebar.slider("Режим DoS-атаки (інтенсивність λ)", 5.0, 30.0, 12.0, step=0.5)

st.sidebar.markdown("---")
attack_start_step = st.sidebar.slider("Початок атаки (крок)", 0, duration_steps, 80)
attack_end_step = st.sidebar.slider("Кінець атаки (крок)", attack_start_step, duration_steps, 180)

st.sidebar.markdown("---")
service_capacity = st.sidebar.number_input("Пропускна здатність (зап./крок)", min_value=1, value=4)
queue_limit = st.sidebar.number_input("Максимальна черга", min_value=5, value=50)
seed = st.sidebar.number_input("Генератор (Seed)", value=42)

# Перевірка логіки кроків атаки
if attack_start_step >= attack_end_step:
    st.sidebar.error("Помилка: Початок атаки має бути раніше її кінця!")

# ==========================================
# ЗАПУСК МОДЕЛЮВАННЯ
# ==========================================
# Збираємо конфігурацію з повзунків Streamlit
config = SimulationConfig(
    duration_steps=duration_steps,
    normal_arrival_rate=normal_arrival_rate,
    attack_arrival_rate=attack_arrival_rate,
    attack_start_step=attack_start_step,
    attack_end_step=attack_end_step,
    service_capacity_per_step=service_capacity,
    queue_limit=queue_limit,
    seed=seed
)

# Виклик твоєї функції симуляції
result = simulate(config)
stats = result["stats"]
series = result["series"]
steps = list(range(config.duration_steps))

# ==========================================
# ВІДОБРАЖЕННЯ РЕЗУЛЬТАТІВ В СТРІМЛІТІ
# ==========================================

# 1. Метрики (Загальні результати)
st.subheader("📊 Ключові показники ефективності вузла")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Всього запитів", int(stats["total_arrivals"]))
    st.metric("Макс. довжина черги", int(stats["peak_queue"]))
with col2:
    st.metric("Оброблено", int(stats["total_served"]))
    st.metric("Сер. довжина черги", f"{stats['average_queue']:.2f}")
with col3:
    st.metric("Втрачено (відхилено)", int(stats["total_dropped"]), delta=int(stats["total_dropped"]), delta_color="inverse")
    st.metric("Сер. час очікування", f"{stats['average_wait_proxy']:.2f}")
with col4:
    st.metric("Частка успішних", f"{stats['service_rate'] * 100:.2f}%")
    st.metric("Частка втрат", f"{stats['drop_rate'] * 100:.2f}%", delta=f"{stats['drop_rate'] * 100:.2f}%", delta_color="inverse")

st.markdown("---")

# 2. Графіки (згідно з переліком графічного матеріалу в завданні)
st.subheader("📈 Графічний аналіз динаміки навантаження")

tab1, tab2, tab3 = st.tabs([
    "📉 Динаміка запитів",
    "⏳ Черга та Очікування",
    "❌ Відхилені запити"
])

with tab1:
    fig1, ax1 = plt.subplots(figsize=(10, 4.5))
    ax1.plot(steps, series["arrivals"], label="Надходження запитів", color="#1f77b4")
    ax1.plot(steps, series["served"], label="Оброблено запитів", color="#ff7f0e")
    ax1.axvspan(config.attack_start_step, config.attack_end_step, alpha=0.15, color="red", label="Період DoS-атаки")
    ax1.set_xlabel("Крок моделювання")
    ax1.set_ylabel("Кількість запитів")
    ax1.title.set_text("Динаміка надходження та обробки запитів")
    ax1.legend()
    st.pyplot(fig1)

with tab2:
    fig2, ax2 = plt.subplots(figsize=(10, 4.5))
    ax2.plot(steps, series["queue"], label="Довжина черги", color="#d62728")
    ax2.plot(steps, series["wait_proxy"], label="Умовний час очікування", color="#2ca02c", linestyle="--")
    ax2.axvspan(config.attack_start_step, config.attack_end_step, alpha=0.15, color="red", label="Період DoS-атаки")
    ax2.set_xlabel("Крок моделювання")
    ax2.set_ylabel("Значення")
    ax2.title.set_text("Зміна довжини черги та часу очікування")
    ax2.legend()
    st.pyplot(fig2)

with tab3:
    fig3, ax3 = plt.subplots(figsize=(10, 4.5))
    ax3.bar(steps, series["dropped"], width=1.0, color="#7f7f7f", label="Втрачені запити")
    ax3.axvspan(config.attack_start_step, config.attack_end_step, alpha=0.15, color="red", label="Період DoS-атаки")
    ax3.set_xlabel("Крок моделювання")
    ax3.set_ylabel("Кількість відхилених запитів")
    ax3.title.set_text("Динаміка відхилення запитів (Втрати трафіку)")
    ax3.legend()
    st.pyplot(fig3)

st.markdown("---")

# 3. Порівняння режимів та фінальний висновок
st.subheader("📝 Аналітичний висновок")

col_left, col_right = st.columns(2)

with col_left:
    st.write("**Порівняльна оцінка режимів роботи вузла:**")
    comparison_data = {
        "Показник": ["Сер. оброблено", "Сер. відхилено"],
        "Штатний режим": [f"{stats['normal_average_served']:.2f}", f"{stats['normal_average_dropped']:.2f}"],
        "Режим атаки": [f"{stats['attack_average_served']:.2f}", f"{stats['attack_average_dropped']:.2f}"]
    }
    st.table(comparison_data)

with col_right:
    st.write("**Підсумкова оцінка наслідків:**")
    if stats["total_dropped"] > 0:
        st.error(
            f"⚠️ **УВАГА:** Моделювання DoS-атаки чітко демонструє критичне перевантаження системи. "
            f"Штучне підвищення інтенсивності вхідного потоку до {config.attack_arrival_rate} зап./крок призвело "
            f"до втрати {int(stats['total_dropped'])} запитів. Середня довжина черги досягла {stats['average_queue']:.2f} "
            f"одиниць, що підтверджує значне зниження доступності мережевого сервісу."
        )
    else:
        st.success(
            "✅ **СТАБІЛЬНО:** За поточних параметрів мережевий вузол успішно впорався із навантаженням. "
            "Черга не переповнилася, втрат легітимних запитів немає. Щоб побачити стан відмови в обслуговуванні, "
            "спробуйте збільшити інтенсивність атаки або зменшити пропускну здатність вузла."
        )