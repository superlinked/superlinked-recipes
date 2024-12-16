# Superlinked Recipes

This repository showcases projects using Superlinked for various use cases: Multi-Modal Semantic Search, Recommendation System, and RAG.

Each project is a standalone application utilizing Superlinked. A public Streamlit app is available for experimentation. Projects can be run locally or via our free-tier cloud solution with GCP. Detailed tutorials are provided for each project.

Superlinked is a framework for building scalable applications with multi-modal vector search. The core is open-source, but the Cloud solution offers additional features like batch-module, CLI, monitoring, and more.

Learn more about Superlinked:
- [Website](https://superlinked.com)
- [GitHub](https://github.com/superlinked/superlinked)
- [Documentation](https://docs.superlinked.com)

## Multi-Modal Semantic Search

Multi-Modal Semantic Search enables you to search across diverse data types by understanding the context and meaning, rather than relying solely on keywords. Superlinked supports various modalities as primary features, including [text](https://github.com/superlinked/superlinked/blob/main/notebook/feature/text_embedding.ipynb), [images](https://github.com/superlinked/superlinked/blob/main/notebook/image_search_e_commerce.ipynb), [numbers](https://github.com/superlinked/superlinked/blob/main/notebook/feature/number_embedding_minmax.ipynb), [categories](https://github.com/superlinked/superlinked/blob/main/notebook/feature/categorical_embedding.ipynb), and [recency](https://github.com/superlinked/superlinked/blob/main/notebook/feature/recency_embedding.ipynb). If you prefer to use your own embeddings, Superlinked offers a [CustomSpace](https://github.com/superlinked/superlinked/blob/main/notebook/feature/custom_space.ipynb) feature to accommodate this need.

Superlinked allows you to fine-tune the importance of different attributes for each query by adjusting [weights at query time](https://github.com/superlinked/superlinked/blob/main/notebook/feature/dynamic_parameters.ipynb), making the process straightforward and intuitive. To further simplify the experience, Superlinked offers a [Natural Language Interface](https://github.com/superlinked/superlinked/blob/main/notebook/feature/natural_language_querying.ipynb), enabling users to input their queries in plain, everyday language.

A standout feature of Superlinked is its ability to handle data objects holistically, eliminating the need for Reciprocal Rank Fusion (RRF), which significantly enhances system performance. For those who require keyword search capabilities, Superlinked also provides Hybrid Search, again without the need for RRF.

Below is a table showcasing projects built using Superlinked, demonstrating the power of multi-modal semantic search.

<table>
  <tr>
    <th valign="top">Recipe</th>
    <th valign="top">Key Features</th>
    <th valign="top">Modalities</th>
  </tr>
  <tr>
    <td valign="top">
      <a href="./projects/hotel-search"><strong>📂 Hotel Search</strong></a><br>
      <a href="https://hotel-search-recipe.superlinked.io/">🚀 Try it now</a><br>
      <!-- <a href="https://www.loom.com/share/not-found">💁 Video walkthrough</a> -->
    </td>
    <td valign="top">
        Natural Language Queries<br>
        Multi-modal Semantic Search<br>
    </td>
    <td valign="top">
        Text<br>
        Numbers<br>
        Categories<br>
    </td>
  </tr>
</table>

## Recommendation System

Recommendation Systems combine Semantic Search and personalization for relevant suggestions based on user preferences.

<table>
  <tr>
    <th valign="top">Recipe</th>
    <th valign="top">Key Features</th>
    <th valign="top">Modalities</th>
  </tr>
  <tr>
    <td valign="top">
      <strong>📂 E-Commerce RecSys</strong><br>
      <a href="https://e-commerce-recsys-recipe.superlinked.io">🚀 Try it now</a><br>
      Code is coming soon!<br>
    </td>
    <td valign="top">
      Item-to-item recommendations<br>
      Item-to-user recommendations<br>
      Collaborative filtering<br>
    </td>
    <td valign="top">
      Images<br>
      Text<br>
      Categories<br>
      Numbers<br>
    </td>
  </tr>
</table>

## RAG

RAG (Retrieval-Augmented Generation) combines semantic search with generation capabilities, retrieving relevant information and generating contextually appropriate responses.

<table>
  <tr>
    <th valign="top">Recipe</th>
    <th valign="top">Key Features</th>
    <th valign="top">Modalities</th>
  </tr>
  <tr>
    <td valign="top">
      <strong>📂 PDF RAG</strong><br>
      Code and demo are coming soon!<br>
    </td>
    <td valign="top">
      Search PDF documents with Natural Language Queries<br>
      Generate responses based on retrieved information<br>
      Conversational follow-up questions<br>
    </td>
    <td valign="top">
    Text<br>
    </td>
  </tr>
</table>
