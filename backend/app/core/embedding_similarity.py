"""
Embedding-Based Similarity System

This module provides semantic similarity search and clustering for lease clauses
using embedding models.
"""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
import json
import os
from dataclasses import dataclass
from app.utils.logger import logger


@dataclass
class EmbeddedClause:
    """Represents a clause with its embedding"""
    clause_id: str
    content: str
    embedding: np.ndarray
    metadata: Dict[str, Any]
    

class EmbeddingService:
    """
    Service for generating embeddings using OpenAI or local models
    """
    
    def __init__(self, model: str = "text-embedding-ada-002"):
        self.model = model
        self.cache = {}  # Simple in-memory cache
        self._client = None
        
    async def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text"""
        # Check cache first
        if text in self.cache:
            return self.cache[text]
            
        try:
            import openai
            
            # Use OpenAI embeddings
            client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            try:
                response = await client.embeddings.create(
                    model=self.model,
                    input=text
                )
            
                embedding = np.array(response.data[0].embedding)
                self.cache[text] = embedding
            
                return embedding
            finally:
                await client.close()
            
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            # Fallback to simple TF-IDF based embedding
            return self._fallback_embedding(text)
            
    def _fallback_embedding(self, text: str) -> np.ndarray:
        """Simple fallback embedding using character n-grams"""
        # This is a very basic fallback - in production use proper embeddings
        vector = np.zeros(384)  # Match typical embedding size
        
        # Simple character trigram features
        for i in range(len(text) - 2):
            trigram = text[i:i+3]
            index = hash(trigram) % len(vector)
            vector[index] += 1
            
        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector
        
    async def get_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Get embeddings for multiple texts efficiently"""
        embeddings = []
        
        # Filter out cached texts
        uncached_texts = [t for t in texts if t not in self.cache]
        
        if uncached_texts:
            try:
                import openai
                
                client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                try:
                    response = await client.embeddings.create(
                        model=self.model,
                        input=uncached_texts
                    )
                
                    # Cache new embeddings
                    for text, emb_data in zip(uncached_texts, response.data):
                        embedding = np.array(emb_data.embedding)
                        self.cache[text] = embedding
                finally:
                    await client.close()
                    
            except Exception as e:
                logger.error(f"Error getting batch embeddings: {e}")
                # Fallback for uncached
                for text in uncached_texts:
                    self.cache[text] = self._fallback_embedding(text)
                    
        # Return all embeddings in order
        return [self.cache[text] for text in texts]


class SemanticChunker:
    """
    Semantic chunking using embeddings to find natural boundaries
    """
    
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.similarity_threshold = 0.7
        
    async def chunk_by_semantic_similarity(self, text: str, 
                                         target_chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """
        Chunk text based on semantic similarity between sentences
        """
        # Split into sentences
        sentences = self._split_into_sentences(text)
        
        if len(sentences) < 2:
            return [{"content": text, "start": 0, "end": len(text)}]
            
        # Get embeddings for all sentences
        embeddings = await self.embedding_service.get_embeddings_batch(sentences)
        
        # Find semantic boundaries
        chunks = []
        current_chunk = [sentences[0]]
        current_start = 0
        
        for i in range(1, len(sentences)):
            # Calculate similarity with previous sentence
            similarity = cosine_similarity(
                embeddings[i-1].reshape(1, -1),
                embeddings[i].reshape(1, -1)
            )[0][0]
            
            # Check if we should start a new chunk
            current_size = sum(len(s) for s in current_chunk)
            
            if (similarity < self.similarity_threshold and current_size > target_chunk_size/2) or \
               current_size > target_chunk_size:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    "content": chunk_text,
                    "start": current_start,
                    "end": current_start + len(chunk_text),
                    "avg_similarity": similarity
                })
                
                # Start new chunk
                current_chunk = [sentences[i]]
                current_start = current_start + len(chunk_text) + 1
            else:
                current_chunk.append(sentences[i])
                
        # Don't forget last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                "content": chunk_text,
                "start": current_start,
                "end": current_start + len(chunk_text)
            })
            
        return chunks
        
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting - in production use nltk or spacy
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]


class ClauseSimilarityFinder:
    """
    Find similar clauses across documents using embeddings
    """
    
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.embedded_clauses: List[EmbeddedClause] = []
        
    async def index_clauses(self, clauses: Dict[str, Any]):
        """Index clauses with embeddings"""
        for clause_id, clause_data in clauses.items():
            content = clause_data.get("content", "")
            if content:
                embedding = await self.embedding_service.get_embedding(content)
                
                embedded_clause = EmbeddedClause(
                    clause_id=clause_id,
                    content=content,
                    embedding=embedding,
                    metadata=clause_data.get("metadata", {})
                )
                
                self.embedded_clauses.append(embedded_clause)
                
        logger.info(f"Indexed {len(self.embedded_clauses)} clauses")
        
    async def find_similar_clauses(self, query_text: str, 
                                 top_k: int = 5,
                                 min_similarity: float = 0.7) -> List[Tuple[str, float]]:
        """Find clauses similar to query text"""
        if not self.embedded_clauses:
            return []
            
        # Get query embedding
        query_embedding = await self.embedding_service.get_embedding(query_text)
        
        # Calculate similarities
        clause_embeddings = np.array([c.embedding for c in self.embedded_clauses])
        similarities = cosine_similarity(
            query_embedding.reshape(1, -1),
            clause_embeddings
        )[0]
        
        # Get top results
        results = []
        for idx, similarity in enumerate(similarities):
            if similarity >= min_similarity:
                results.append((
                    self.embedded_clauses[idx].clause_id,
                    float(similarity)
                ))
                
        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
        
    def find_duplicate_clauses(self, similarity_threshold: float = 0.95) -> List[List[str]]:
        """Find groups of duplicate/near-duplicate clauses"""
        if len(self.embedded_clauses) < 2:
            return []
            
        # Calculate pairwise similarities
        embeddings = np.array([c.embedding for c in self.embedded_clauses])
        similarity_matrix = cosine_similarity(embeddings)
        
        # Use DBSCAN clustering
        clustering = DBSCAN(
            eps=1-similarity_threshold,  # Convert similarity to distance
            min_samples=2,
            metric='precomputed'
        )
        
        # Convert similarity to distance matrix
        distance_matrix = 1 - similarity_matrix
        # Ensure no negative values due to floating point precision
        distance_matrix = np.maximum(distance_matrix, 0)
        # Ensure diagonal is exactly 0
        np.fill_diagonal(distance_matrix, 0)
        labels = clustering.fit_predict(distance_matrix)
        
        # Group clauses by cluster
        clusters = {}
        for idx, label in enumerate(labels):
            if label != -1:  # Ignore noise
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(self.embedded_clauses[idx].clause_id)
                
        return list(clusters.values())
        
    def find_outlier_clauses(self, contamination: float = 0.1) -> List[str]:
        """Find unusual/outlier clauses"""
        if len(self.embedded_clauses) < 10:
            return []
            
        embeddings = np.array([c.embedding for c in self.embedded_clauses])
        
        # Calculate average similarity to other clauses
        similarity_matrix = cosine_similarity(embeddings)
        avg_similarities = np.mean(similarity_matrix, axis=1)
        
        # Find clauses with lowest average similarity
        threshold = np.percentile(avg_similarities, contamination * 100)
        outliers = []
        
        for idx, avg_sim in enumerate(avg_similarities):
            if avg_sim <= threshold:
                outliers.append(self.embedded_clauses[idx].clause_id)
                
        return outliers


class CrossDocumentSimilarity:
    """
    Find similar provisions across multiple documents
    """
    
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.document_clauses: Dict[str, ClauseSimilarityFinder] = {}
        
    async def index_document(self, doc_id: str, clauses: Dict[str, Any]):
        """Index clauses from a document"""
        finder = ClauseSimilarityFinder(self.embedding_service)
        await finder.index_clauses(clauses)
        self.document_clauses[doc_id] = finder
        
    async def find_cross_document_similarities(self, 
                                             min_similarity: float = 0.8) -> List[Dict[str, Any]]:
        """Find similar clauses across documents"""
        similarities = []
        
        # Get all clauses from all documents
        all_clauses = []
        for doc_id, finder in self.document_clauses.items():
            for clause in finder.embedded_clauses:
                all_clauses.append({
                    "doc_id": doc_id,
                    "clause_id": clause.clause_id,
                    "embedding": clause.embedding,
                    "content": clause.content
                })
                
        # Compare all pairs
        for i in range(len(all_clauses)):
            for j in range(i + 1, len(all_clauses)):
                if all_clauses[i]["doc_id"] != all_clauses[j]["doc_id"]:
                    similarity = cosine_similarity(
                        all_clauses[i]["embedding"].reshape(1, -1),
                        all_clauses[j]["embedding"].reshape(1, -1)
                    )[0][0]
                    
                    if similarity >= min_similarity:
                        similarities.append({
                            "doc1": all_clauses[i]["doc_id"],
                            "clause1": all_clauses[i]["clause_id"],
                            "doc2": all_clauses[j]["doc_id"],
                            "clause2": all_clauses[j]["clause_id"],
                            "similarity": float(similarity),
                            "sample1": all_clauses[i]["content"][:100],
                            "sample2": all_clauses[j]["content"][:100]
                        })
                        
        # Sort by similarity
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similarities
        
    def find_standard_clauses(self, min_occurrences: int = 3) -> List[Dict[str, Any]]:
        """Find clauses that appear in multiple documents (standard language)"""
        # Find groups of similar clauses across documents
        clause_groups = []
        
        # This is simplified - in production, use more sophisticated clustering
        all_clauses = []
        for doc_id, finder in self.document_clauses.items():
            for clause in finder.embedded_clauses:
                all_clauses.append({
                    "doc_id": doc_id,
                    "clause_id": clause.clause_id,
                    "embedding": clause.embedding,
                    "content": clause.content[:200]
                })
                
        if len(all_clauses) < min_occurrences:
            return []
            
        # Simple clustering based on high similarity
        embeddings = np.array([c["embedding"] for c in all_clauses])
        similarity_matrix = cosine_similarity(embeddings)
        
        # Find groups with high similarity
        groups = []
        used = set()
        
        for i in range(len(all_clauses)):
            if i in used:
                continue
                
            group = [i]
            for j in range(i + 1, len(all_clauses)):
                if j not in used and similarity_matrix[i][j] > 0.9:
                    group.append(j)
                    used.add(j)
                    
            if len(group) >= min_occurrences:
                # Check if from different documents
                doc_ids = set(all_clauses[idx]["doc_id"] for idx in group)
                if len(doc_ids) >= min_occurrences:
                    groups.append({
                        "clause_indices": group,
                        "documents": list(doc_ids),
                        "sample": all_clauses[group[0]]["content"],
                        "occurrences": len(group)
                    })
                    
        return groups
