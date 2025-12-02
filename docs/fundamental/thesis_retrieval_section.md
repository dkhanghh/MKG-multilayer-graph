# 4. Retrieval Component: Question-Aware Subgraph Retrieval

## 4.1 Overview

In the context of a Multi-layer Knowledge Graph (MKG) for the financial domain, standard retrieval methods often fail to capture the structural dependencies required to answer complex queries (e.g., "How does Company A's revenue compare to its subsidiary's profit?"). Traditional vector search retrieves isolated nodes based on semantic similarity, losing the relational context. To address this, we propose a **Question-Aware Subgraph Retrieval (QASR)** mechanism.

The QASR method is designed to dynamically construct a relevant subgraph $G_{sub} \subseteq G$ that contains not only the entities mentioned in the query but also the specific relationships and properties requested. This process bridges the semantic gap between unstructured natural language queries and the structured schema of the knowledge graph.

## 4.2 Formal Definition

Let the Multi-layer Knowledge Graph be defined as $G = (V, E, \mathcal{T}, \mathcal{P})$, where:
*   $V = V_{entity} \cup V_{chunk}$ represents the set of nodes, partitioned into semantic entities ($V_{entity}$) and source text chunks ($V_{chunk}$).
*   $E \subseteq V \times V$ represents the set of directed edges.
*   $\mathcal{T}$ denotes the set of edge types (e.g., `OWNS`, `REPORTED_FINANCIALS`).
*   $\mathcal{P}$ denotes the set of properties associated with nodes and edges.

Given a natural language query $q$, the objective is to retrieve a subgraph $G_q = (V_q, E_q)$ such that $G_q$ maximizes the information density relevant to $q$ while minimizing irrelevant noise.

## 4.3 Methodology

The retrieval process operates in a four-stage pipeline: (1) Seed Entity Identification, (2) Schema-Aware Intent Inference, (3) Constrained Subgraph Expansion, and (4) Context Enrichment.

### 4.3.1 Stage 1: Seed Entity Identification via Vector Space Model

The first step is to ground the unstructured query $q$ into the graph by identifying "seed" entities. We utilize a dense vector embedding model $M_{emb}$ to map both the query and graph entities into a shared $d$-dimensional vector space $\mathbb{R}^d$.

For each entity $v \in V_{entity}$, let $\mathbf{e}_v = M_{emb}(v_{name})$ be its embedding vector. Similarly, let $\mathbf{q} = M_{emb}(q)$ be the query embedding. We define the set of seed entities $S_q$ as the top-$k$ entities maximizing the cosine similarity with the query:

$$
S_q = \left\{ v \in V_{entity} \mid \text{sim}(\mathbf{e}_v, \mathbf{q}) \ge \tau \right\}
$$

where $\text{sim}(\mathbf{a}, \mathbf{b}) = \frac{\mathbf{a} \cdot \mathbf{b}}{\|\mathbf{a}\| \|\mathbf{b}\|}$ and $\tau$ is a relevance threshold. This stage effectively filters the search space from $|V|$ to $|S_q|$, where $|S_q| \ll |V|$.

### 4.3.2 Stage 2: Semantic Schema Alignment

To generalize beyond rigid keyword matching, we employ a semantic alignment mechanism to map the user's intent to the graph schema. Let $\mathcal{T}$ be the set of available relationship types in the graph (e.g., `REPORTED_FINANCIALS`, `OWNS`). We associate each type $t \in \mathcal{T}$ with a natural language description $d_t$ (e.g., "financial performance, revenue, profit, and earnings reports").

We compute the semantic similarity between the query embedding $\mathbf{q}$ and the embedding of each relationship description $\mathbf{e}_{d_t} = M_{emb}(d_t)$. The set of relevant relationship types $T_q$ is selected based on a semantic threshold $\delta$:

$$
T_q = \{ t \in \mathcal{T} \mid \text{sim}(\mathbf{q}, \mathbf{e}_{d_t}) \ge \delta \}
$$

This approach allows the system to infer the correct relationship types even when the user employs synonyms or domain-specific jargon not explicitly present in the schema names (e.g., mapping "top line growth" to `REPORTED_FINANCIALS`). If no types exceed the threshold (i.e., $T_q = \emptyset$), the system defaults to an unconstrained traversal to ensure high recall.

### 4.3.3 Stage 3: Constrained Subgraph Expansion

Starting from the seed set $S_q$, we perform a constrained $k$-hop traversal to construct the answer subgraph. Let $V^{(0)} = S_q$. The set of nodes at hop $i$ ($V^{(i)}$) is defined recursively:

$$
V^{(i)} = V^{(i-1)} \cup \left\{ v' \in V \mid \exists v \in V^{(i-1)}, e=(v, v') \in E \text{ s.t. } \text{type}(e) \in T_q \right\}
$$

The final node set for the subgraph is $V_q = \bigcup_{i=0}^{k} V^{(i)}$, where $k$ is the maximum hop depth (typically $k=2$). The edge set $E_q$ consists of all edges between nodes in $V_q$ that satisfy the type constraint:

$$
E_q = \{ (u, v) \in E \mid u, v \in V_q \wedge \text{type}((u, v)) \in T_q \}
$$

This constrained expansion allows the system to retrieve multi-hop reasoning chains (e.g., *Company A* $\xrightarrow{\texttt{OWNS}}$ *Company B* $\xrightarrow{\texttt{REPORTED\_FINANCIALS}}$ *Revenue*) while avoiding "graph explosion" by strictly following the inferred schema types.

### 4.3.4 Stage 4: Context Enrichment and Property Filtering

The final stage enriches the structural skeleton $G_q$ with unstructured evidence from the document layer. For each node $v \in V_q$, we retrieve connected chunk nodes $c \in V_{chunk}$ via the `SOURCE` relationship:

$$
C_v = \{ c \in V_{chunk} \mid (c, v) \in E \wedge \text{type}((c, v)) = \texttt{SOURCE} \}
$$

Additionally, we apply a property filter $P_{filter}$ to edges in $E_q$. If the query contains temporal or quantitative constraints (e.g., "2023"), we retain only those edges where properties match the constraints:

$$
E_q' = \{ e \in E_q \mid \forall (k, val) \in \text{props}(e), \text{match}(val, q) \}
$$

## 4.4 Output Generation

The final retrieved context $\mathcal{C}_{final}$ is a serialization of the enriched subgraph:

$$
\mathcal{C}_{final} = \text{Serialize}(G_q, \{C_v\}_{v \in V_q})
$$

This structured representation provides the Large Language Model (LLM) with both the *explicit facts* (from graph structure) and the *supporting evidence* (from text chunks), enabling high-fidelity generation for financial analysis tasks.
