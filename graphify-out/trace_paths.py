import json, sys
import networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path
from collections import defaultdict

data = json.loads(Path('graphify-out/graph.json').read_text(encoding='utf-8'))
G = json_graph.node_link_graph(data, edges='links')

targets = {
    'governance_kernel_governancekernel': 'GovernanceKernel',
    'accounting_models_account': 'Account',
    'accounting_models_journalentry': 'JournalEntry',
    'services_journal_engine_journalengine': 'JournalEngine',
}

# For each target, find the top 20 strongest incoming edges by weight + confidence
for nid, label in targets.items():
    if nid not in G.nodes:
        print(f"Node {nid} not found!")
        continue
    
    # Get all neighbors with edge data
    edges_with_data = []
    for neighbor in G.neighbors(nid):
        edge_data = G.get_edge_data(nid, neighbor)
        if edge_data:
            # Handle MultiGraph vs Graph
            if isinstance(edge_data, dict) and 0 in edge_data:
                ed = edge_data[0]
            elif isinstance(edge_data, dict):
                ed = edge_data
            else:
                ed = {}
            
            weight = ed.get('weight', 1.0)
            confidence = ed.get('confidence', 'UNKNOWN')
            conf_score = ed.get('confidence_score', 0.5)
            relation = ed.get('relation', 'unknown')
            source_file = ed.get('source_file', '')
            
            # Score: weight * confidence_score, boosted for EXTRACTED
            boost = 1.5 if confidence == 'EXTRACTED' else 1.0 if confidence == 'INFERRED' else 0.5
            score = weight * conf_score * boost
            
            neighbor_label = G.nodes[neighbor].get('label', neighbor)
            neighbor_file = G.nodes[neighbor].get('source_file', '')
            neighbor_type = G.nodes[neighbor].get('file_type', 'unknown')
            
            edges_with_data.append({
                'score': score,
                'neighbor_id': neighbor,
                'neighbor_label': neighbor_label,
                'neighbor_file': neighbor_file,
                'neighbor_type': neighbor_type,
                'relation': relation,
                'confidence': confidence,
                'conf_score': conf_score,
                'weight': weight,
                'source_file': source_file,
            })
    
    # Sort by score descending
    edges_with_data.sort(key=lambda x: -x['score'])
    
    print(f"\n{'='*80}")
    print(f"TARGET: {label} ({nid}) — degree {G.degree(nid)}")
    print(f"{'='*80}")
    
    for i, e in enumerate(edges_with_data[:20]):
        print(f"\n  [{i+1}] {e['neighbor_label']}")
        print(f"      relation: {e['relation']}  confidence: {e['confidence']} ({e['conf_score']})  score: {e['score']:.2f}")
        print(f"      source: {e['neighbor_file']}")
        print(f"      edge from: {e['source_file']}")
