import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events
import altair as alt

# importa a função que foi criada para analise de dados
from ai_analyst import get_gpt_analysis

st.set_page_config(layout='wide')
titulo, = st.columns(1)
col5, col6, col7, col8, col9 = st.columns(5)
coluna0, = st.columns(1)
col2, = st.columns(1)
col3, = st.columns(1)

# --- Cor ---
titulo.markdown(
    """
    <p style="
        background-color: #0E1117; 
        color: #ADD8E6;
        font-size: 38px;
        font-weight: bold;
        text-align: center;
        border-radius: 10px;
        padding: 10px;
        border: 2px  #262730;
    ">
        Análise Faturamento
    </p>
    """,
    unsafe_allow_html=True
)

st.sidebar.header("Carregar Novo Arquivo")
uploaded_file = st.sidebar.file_uploader(
    "Escolha um arquivo Excel (.xlsx)",
    type=['xlsx', 'xls']
)
# 2. LÓGICA DE DECISÃO
# Se um arquivo foi enviado pelo usuário, use-o.
if uploaded_file is not None:
    st.sidebar.success("Arquivo carregado com sucesso! Usando os novos dados.")
    fonte_dados = uploaded_file
# Se nenhum arquivo foi enviado, use o arquivo padrão.
else:
    fonte_dados = "faturamento.xlsx"


def formatar_moeda(valor):
    """Formata um número para o padrão de moeda brasileiro (R$ 1.234,56)."""
    if pd.isna(valor):
        return "0,00"
    # O truque para trocar os separadores
    valor_formatado = f"{valor:,.2f}".replace(
        ",", "X").replace(".", ",").replace("X", ".")
    return f"{valor_formatado}"


@st.cache_data
def carregar_dados(fonte_dados):

    try:
        df = pd.read_excel(fonte_dados)
        # st.write("Colunas", df.columns.tolist()) #printa as colunas do dataset na tela
    except FileNotFoundError:
        st.error(f"Arquivo {fonte_dados} não foi encontrado!")
        return pd.DataFrame
    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo {e}")
        return pd.DataFrame()

    if not df.empty:
        df.rename(columns={
            'Nome Correntista': 'nome_cliente',
            'Nome Vendedor': 'nome_vendedor',
            'nome_classe': 'classe_produto',
            'nome_grupo': 'grupo_produto',
            'nome_subgrupo': 'subgrupo_produto',
            'nome_familia': 'familia_produto',
            'nome_segmento': 'segmento_produto',
            'Descrição Item': 'descricao_item',
            'Quantidade': 'quantidade',
            'Peso Bruto': 'peso_bruto',
            'Peso': 'Peso',
            'Unitário': 'valor_unitario',
            'Total Item': 'valor_total_item',
            'Data Emissão': 'data_emissao',
            'descricao_tpvenda': 'tipo_venda'
        }, inplace=True)  # inplace true, comita a mudança para o script
        # formata campos como data coerce significa retornar um valor com não é data qdo não consegui converter.
        df['data_emissao'] = pd.to_datetime(
            df['data_emissao'], errors='coerce')
        colunas_numericas = ['quantidade', 'peso_bruto',
                             'valor_unitario', 'valor_total_item']

        for col in colunas_numericas:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.dropna(subset=['data_emissao', 'valor_total_item',
                  'nome_vendedor', 'grupo_produto'], inplace=True)

    return df


meses_em_portugues = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro"
}

data_set = carregar_dados(fonte_dados)
data_set["mes_string"] = data_set['data_emissao'].dt.month.map(
    meses_em_portugues)

data_set["competencia"] = data_set["mes_string"] + \
    '/' + data_set["data_emissao"].dt.year.astype(str)


st.sidebar.header("Filtros")
data_set_filtrado = data_set.copy()

opcoes_competencia = data_set['competencia'].unique()

comp_selecao = st.sidebar.multiselect(
    "Competência",
    options=opcoes_competencia,
    default=[]
)

if comp_selecao:
    data_set_filtrado = data_set_filtrado[
        data_set_filtrado['competencia'].isin(comp_selecao)
    ]

df_vendedor = data_set['nome_vendedor'].unique()


opcoes_vendedor = data_set_filtrado['nome_vendedor'].unique()

vendedor_selecao = st.sidebar.multiselect(
    "Vendedor (opcional)",
    options=opcoes_vendedor,
    default=[]
)
inverter_filtro_vendedor = st.sidebar.toggle(
    "Excluir vendedores selecionados",
    key="inverter_vendedor"  # Uma 'key' única é boa prática
)

if vendedor_selecao:
    # Cria a condição base do filtro
    condicao_base = data_set_filtrado['nome_vendedor'].isin(vendedor_selecao)

    # Verifica o estado do botão 'toggle'
    if inverter_filtro_vendedor:
        # Se o botão estiver LIGADO, inverte a condição com o til (~)
        data_set_filtrado = data_set_filtrado[~condicao_base]
    else:
        # Se o botão estiver DESLIGADO, aplica o filtro normalmente
        data_set_filtrado = data_set_filtrado[condicao_base]


if not data_set.empty:
    selecao_legenda = alt.selection_multi(
        fields=['nome_vendedor'], bind='legend')
    grafico_barra = alt.Chart(data_set_filtrado).mark_bar().encode(
        x=alt.X('nome_vendedor:N',
                sort='y',
                title="Vendedor"
                ),
        y=alt.Y('sum(valor_total_item):Q',
                title="Total de vendas"),
        color=alt.Color('nome_vendedor:N',
                        title='Vendedor',
                        legend=alt.Legend(title="Vendedor")),

        opacity=alt.condition(selecao_legenda, alt.value(1.0), alt.value(0.2)),

        tooltip=[
            alt.Tooltip('nome_vendedor', title='Vendedor'),
            alt.Tooltip('sum(valor_total_item)',
                        title='Vendas Totais', format='$,.2f')
        ]

    ).properties(
        title=f"Ranking de Vendas Por Vendedores({comp_selecao})"
    ).add_params(
        selecao_legenda
    )

    grafico_combinado = (grafico_barra)

    coluna0.markdown("---")
    with coluna0:
        st.altair_chart(grafico_barra)

    coluna0.markdown("---")
# --- GRÁFICO DE LINHA DE VENDAS DIÁRIAS ---

col2.markdown(
    """
    <p style="
        background-color: #0E1117; 
        color: #ADD8E6;
        font-size: 28px;
        font-weight: bold;
        text-align: center;
        border-radius: 10px;
        padding: 10px;
        border: 2px  #262730;
    ">
        Análise de faturamento Diário
    </p>
    """,
    unsafe_allow_html=True
)


grafico_linha = alt.Chart(data_set_filtrado).mark_line().encode(
    x=alt.X('date(data_emissao):T', title='Dia do Mês'),
    y='sum(valor_total_item):Q',
    color='competencia:N'
)
col2.altair_chart(grafico_linha)
col2.markdown("---")

# --- GRÁFICO DE BARRAS EMPILHADAS (ALTAIR) ---

col3.markdown(
    """
    <p style="
        background-color: #0E1117; 
        color: #ADD8E6;
        font-size: 28px;
        font-weight: bold;
        text-align: center;
        border-radius: 10px;
        padding: 10px;
        border: 2px  #262730;
    ">
        Análise por Classificação de  Produto
    </p>
    """,
    unsafe_allow_html=True
)

# Garante que a coluna usada para a cor não tenha valores vazios
data_set_filtrado['grupo_produto'] = data_set_filtrado['grupo_produto'].fillna(
    'Não Especificado')


if not data_set_filtrado.empty:
    data_set_filtrado['grupo_produto'] = data_set_filtrado['grupo_produto'].fillna(
        'Não Especificado')

    grafico_barra_unica_horizontal = alt.Chart(data_set_filtrado).transform_joinaggregate(
        # PASSO 1: Pré-calcula a soma total para cada grupo_produto
        # e cria uma nova "coluna virtual" chamada 'total_vendas_grupo'
        total_vendas_grupo='sum(valor_total_item)',
        groupby=['grupo_produto']
    ).mark_bar(
        size=50  # Mantém a barra mais larga
    ).encode(
        x=alt.X(
            'sum(valor_total_item):Q',
            title='Percentual de Vendas',
            stack='normalize',
            axis=alt.Axis(format='%')
        ),

        y=alt.Y('Composição:N', title='', axis=None),

        color=alt.Color(
            'grupo_produto:N',
            title='Grupo de Produto',
            scale=alt.Scale(scheme='tableau10')
        ),

        # PASSO 2: Força a ordem de empilhamento usando a coluna pré-calculada
        order=alt.Order(
            'total_vendas_grupo:Q',  # Ordena pela soma que calculamos no transform
            sort='descending'
        ),

        tooltip=[
            alt.Tooltip('grupo_produto', title='Grupo'),
            alt.Tooltip('sum(valor_total_item):Q',
                        title='Vendas', format='$,.2f')
        ]
    ).properties(
        title='Participação de Cada Grupo no Faturamento Total'
    )


else:
    st.info("Nenhum dado encontrado para os filtros selecionados.")

col3.altair_chart(grafico_barra_unica_horizontal, use_container_width=True)


if not data_set_filtrado.empty:
    data_set_filtrado['classe_produto'] = data_set_filtrado['classe_produto'].fillna(
        'Não Especificado')

    grafico_barra_unica_horizontal = alt.Chart(data_set_filtrado).transform_joinaggregate(
        # PASSO 1: Pré-calcula a soma total para cada grupo_produto
        # e cria uma nova "coluna virtual" chamada 'total_vendas_grupo'
        total_vendas_grupo='sum(valor_total_item)',
        groupby=['classe_produto']
    ).mark_bar(
        size=50  # Mantém a barra mais larga
    ).encode(
        x=alt.X(
            'sum(valor_total_item):Q',
            title='Percentual de Vendas',
            stack='normalize',
            axis=alt.Axis(format='%')
        ),

        y=alt.Y('Composição:N', title='', axis=None),

        color=alt.Color(
            'classe_produto:N',
            title='Classe de Produto',
            scale=alt.Scale(scheme='tableau10')
        ),

        # PASSO 2: Força a ordem de empilhamento usando a coluna pré-calculada
        order=alt.Order(
            'total_vendas_grupo:Q',  # Ordena pela soma que calculamos no transform
            sort='descending'
        ),

        tooltip=[
            alt.Tooltip('classe_produto', title='Grupo'),
            alt.Tooltip('sum(valor_total_item):Q',
                        title='Vendas', format='$,.2f')
        ]
    ).properties(
        title='Participação de Cada Grupo no Faturamento Total'
    )

    st.altair_chart(grafico_barra_unica_horizontal, use_container_width=True)
else:
    st.info("Nenhum dado encontrado para os filtros selecionados.")


if not data_set_filtrado.empty:
    data_set_filtrado['familia_produto'] = data_set_filtrado['familia_produto'].fillna(
        'Não Especificado')

    grafico_barra_unica_horizontal = alt.Chart(data_set_filtrado).transform_joinaggregate(
        # PASSO 1: Pré-calcula a soma total para cada grupo_produto
        # e cria uma nova "coluna virtual" chamada 'total_vendas_grupo'
        total_vendas_grupo='sum(valor_total_item)',
        groupby=['familia_produto']
    ).mark_bar(
        size=50  # Mantém a barra mais larga
    ).encode(
        x=alt.X(
            'sum(valor_total_item):Q',
            title='Percentual de Vendas',
            stack='normalize',
            axis=alt.Axis(format='%')
        ),

        y=alt.Y('Composição:N', title='', axis=None),

        color=alt.Color(
            'familia_produto:N',
            title='familia de Produto',
            scale=alt.Scale(scheme='tableau10')
        ),

        # PASSO 2: Força a ordem de empilhamento usando a coluna pré-calculada
        order=alt.Order(
            'total_vendas_grupo:Q',  # Ordena pela soma que calculamos no transform
            sort='descending'
        ),

        tooltip=[
            alt.Tooltip('familia_produto', title='Família'),
            alt.Tooltip('sum(valor_total_item):Q',
                        title='Faturamento', format='$,.2f')
        ]
    ).properties(
        title='Participação de Cada familia no Faturamento Total'
    )

    st.altair_chart(grafico_barra_unica_horizontal, use_container_width=True)
else:
    st.info("Nenhum dado encontrado para os filtros selecionados.")

# 1. CALCULAR OS INDICADORES
faturamento_total = data_set_filtrado['valor_total_item'].sum()
vendedores_unicos = data_set_filtrado['nome_vendedor'].nunique()
# Proteção contra divisão por zero se o dataframe estiver vazio
ticket_medio = faturamento_total / \
    len(data_set_filtrado) if len(data_set_filtrado) > 0 else 0

# NOVOS CÁLCULOS DE PESO
peso_total = data_set_filtrado['peso_bruto'].sum()
peso_medio_por_linha = peso_total / \
    len(data_set_filtrado) if not data_set_filtrado.empty else 0

valor_por_quilo = faturamento_total / peso_total if peso_total > 0 else 0

with col5:
    st.metric("Faturamento Total", value=f"R${formatar_moeda(faturamento_total)}"
              )

with col6:
    st.metric("Ticket Médio por Item",
              value=f"R$ {formatar_moeda(ticket_medio)}"
              )

with col7:
    st.metric("Peso Total",
              value=f"{formatar_moeda(peso_total)} Kg"
              )

with col8:
    st.metric(
        label="Ticket Médio (Peso)",
        value=f"{formatar_moeda(peso_medio_por_linha)} Kg"
    )
with col9:
    st.metric(
        label="Fator Quilo",
        value=f"R$/Kg {formatar_moeda(valor_por_quilo)}"
    )
# aqui irá ser gerado a analise de implementação do dashboard
coluna_llm, = st.columns(1)

with coluna_llm:
    coluna_llm.markdown("---")

    # adiciona formatação para o Resumo

    with coluna_llm:
        st.markdown("---")

        st.markdown(
            """
            <p style="
                background-color: #0E1117; 
                color: #7FFF00; 
                font-size: 28px;
                font-weight: bold;
                text-align: center;
                border-radius: 10px;
                padding: 10px;
                border: 2px #262730;
            ">
                Análise de Insights Estruturados por IA (GPT-4o mini)
            </p>
            """,
            unsafe_allow_html=True
        )

    if not data_set_filtrado.empty:
        # top 5 grupos maior valor
        top_grupos = data_set_filtrado.groupby(
            'grupo_produto')['valor_total_item'].sum().nlargest(5).index.tolist()
        df_grupos = data_set_filtrado[data_set_filtrado['grupo_produto'].isin(
            top_grupos)]
        estatistica_por_grupo = df_grupos.groupby(
            'grupo_produto')[['valor_total_item', 'quantidade']].describe().transpose()

        # top 5 vendedores
        top_venddores = data_set_filtrado.groupby(
            'nome_vendedor')['valor_total_item'].sum().nlargest(5).transpose()
        df_vendedor = data_set_filtrado[data_set_filtrado['nome_vendedor'].isin(
            top_venddores)]
        estatistica_por_vendedor = df_vendedor.groupby(
            'nome_vendedor')[['valor_total_item', 'quantidade']].describe().transpose()

        # string de entrada para a LLM
        estatistica_string = (
            f"{estatistica_por_grupo.to_markdown(floatfmt='.2f')}\n\n"
            f"{estatistica_por_vendedor.to_markdown(floatfmt='.2f')}"
        )
        # Mensagem de instrução personalizada para a LLM,
        instrucao_foco = (
            "Gere insights críticos em dois blocos de texto nomeados."
            "O primeiro bloco deve começar obrigatoriamente com o marcador **'--ANÁLISE-PRODUTO--'** e conter 3 insights sobre os GRUPOS."
            "O segundo bloco deve começar obrigatoriamente com o marcador **'--ANÁLISE-PESSOA--'** e conter 3 insights sobre os VENDEDORES."
            "**MANTENHA OS NOMES DAS ENTIDADES RIGIDAMENTE SEPARADOS.**"
        )

    @st.cache_data(show_spinner="Analisando dados com IA...")
    def analisar_dados_com_ia(data_string, instruction):
        # chama a função
        return get_gpt_analysis(
            statistics_data_string=data_string,
            custom_instruction=instruction
        )

    # chama a função
    analise_interpretada = analisar_dados_com_ia(
        estatistica_string, instrucao_foco
    )

    # Exibe o resultado
    coluna_llm.markdown(analise_interpretada)
