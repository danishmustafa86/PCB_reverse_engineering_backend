"""
Schematic Building Module

This module builds a circuit graph using NetworkX and generates a visual
schematic diagram using Schemdraw. It analyzes component positions and
copper track connections to create a netlist and schematic.
"""

import networkx as nx
import schemdraw
import schemdraw.elements as elm
from typing import List, Dict, Any, Tuple
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server
import matplotlib.pyplot as plt
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CircuitGraph:
    """
    Circuit graph representation using NetworkX.
    
    Nodes represent components, edges represent connections via copper tracks.
    """
    
    def __init__(self):
        self.graph = nx.Graph()
        self.components = []
        self.connections = []
        
    def add_component(self, component_id: str, component_type: str, bbox: dict):
        """
        Add a component as a node in the graph.
        
        Args:
            component_id (str): Unique component identifier (e.g., "R1", "NE555")
            component_type (str): Component class (e.g., "Resistor", "IC")
            bbox (dict): Bounding box coordinates
        """
        self.graph.add_node(component_id, 
                          component_type=component_type,
                          bbox=bbox)
        self.components.append({
            'id': component_id,
            'type': component_type,
            'bbox': bbox
        })
        logger.info(f"Added component node: {component_id} ({component_type})")
        
    def add_connection(self, component1_id: str, component2_id: str):
        """
        Add a connection (edge) between two components.
        
        Args:
            component1_id (str): First component ID
            component2_id (str): Second component ID
        """
        if component1_id != component2_id:  # Avoid self-loops
            self.graph.add_edge(component1_id, component2_id)
            connection_str = f"{component1_id} -- {component2_id}"
            if connection_str not in self.connections:
                self.connections.append(connection_str)
                logger.info(f"Added connection: {connection_str}")
    
    def get_netlist(self) -> List[str]:
        """
        Get the netlist as a list of connection strings.
        
        Returns:
            List[str]: List of connection strings (e.g., ["R1 -- U1", "U1 -- C1"])
        """
        return self.connections
    
    def get_component_list(self) -> List[Dict[str, Any]]:
        """
        Get the list of all components.
        
        Returns:
            List[Dict]: List of component dictionaries
        """
        return self.components


def build_circuit_graph(components: List[Dict[str, Any]], 
                       binary_track_image: np.ndarray) -> CircuitGraph:
    """
    Build a circuit graph from components and track image.
    
    INTERSECTION LOGIC:
    This function checks if copper tracks (white pixels in binary_track_image)
    overlap with component bounding boxes. If Track A touches both Component R1
    and Component U1, a connection edge (R1)---(U1) is created in the graph.
    
    Algorithm:
    1. Add all components as nodes
    2. For each pair of components:
       - Check if there's a continuous track path between them
       - Sample points around each component's bbox perimeter
       - If both components touch the same track region, add connection
    
    Args:
        components (List[Dict]): List of components with 'id', 'type', 'bbox'
        binary_track_image (np.ndarray): Binary image with tracks in white
        
    Returns:
        CircuitGraph: Constructed circuit graph
    """
    graph = CircuitGraph()
    
    # Add all components as nodes
    for comp in components:
        graph.add_component(comp['id'], comp['type'], comp['bbox'])
    
    logger.info("Starting connection detection using intersection logic...")
    
    # Check connections between each pair of components
    # INTERSECTION LOGIC: Check if tracks connect component pairs
    for i, comp1 in enumerate(components):
        for j, comp2 in enumerate(components):
            if i >= j:  # Avoid duplicate checks and self-connections
                continue
            
            # Check if there's a track path connecting these components
            if are_components_connected(comp1, comp2, binary_track_image):
                graph.add_connection(comp1['id'], comp2['id'])
    
    logger.info(f"Circuit graph built with {len(graph.components)} components "
               f"and {len(graph.connections)} connections")
    
    return graph


def are_components_connected(comp1: Dict, comp2: Dict, 
                            binary_image: np.ndarray) -> bool:
    """
    Determine if two components are connected via copper tracks.
    
    INTERSECTION LOGIC:
    - Extract the region between the two component bounding boxes
    - Check if there's a continuous white path (track) connecting them
    - This is a simplified heuristic: checks if both components touch tracks
      and the tracks are in proximity
    
    Args:
        comp1 (Dict): First component with 'bbox'
        comp2 (Dict): Second component with 'bbox'
        binary_image (np.ndarray): Binary track image
        
    Returns:
        bool: True if components are likely connected by tracks
    """
    from app.services.tracer import check_track_component_overlap
    
    # Check if each component overlaps with tracks. We require that a
    # reasonable fraction of the sampled perimeter points actually touch
    # tracks (min_hit_ratio) to avoid almost-everything being considered
    # "connected" on noisy masks.
    comp1_has_track = check_track_component_overlap(
        binary_image, comp1['bbox'], sample_points=12, min_hit_ratio=0.35
    )
    comp2_has_track = check_track_component_overlap(
        binary_image, comp2['bbox'], sample_points=12, min_hit_ratio=0.35
    )
    
    if not (comp1_has_track and comp2_has_track):
        return False  # At least one component doesn't touch any tracks
    
    # Calculate distance between components
    x1 = comp1['bbox']['x']
    y1 = comp1['bbox']['y']
    x2 = comp2['bbox']['x']
    y2 = comp2['bbox']['y']
    
    distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    # Heuristic: If components are close and both touch tracks, they are
    # *potentially* connected. The original threshold (500 px) produced
    # extremely dense graphs. We tighten this significantly so that only
    # spatially-near neighbours are considered.
    # This value can be tuned based on image resolution and PCB density.
    max_connection_distance = 140  # pixels
    
    if distance < max_connection_distance:
        # Additional check: verify track continuity in the region between components
        has_continuous_path = check_track_continuity(comp1['bbox'], comp2['bbox'], 
                                                     binary_image)
        return has_continuous_path
    
    return False


def check_track_continuity(bbox1: Dict, bbox2: Dict, 
                           binary_image: np.ndarray) -> bool:
    """
    Check if there's track continuity between two component bounding boxes.
    
    Creates a rectangular region between the two components and checks
    if sufficient track pixels exist in that region.
    
    Args:
        bbox1 (Dict): First component bbox
        bbox2 (Dict): Second component bbox
        binary_image (np.ndarray): Binary track image
        
    Returns:
        bool: True if tracks exist between components
    """
    x1, y1 = int(bbox1['x']), int(bbox1['y'])
    x2, y2 = int(bbox2['x']), int(bbox2['y'])
    
    # Define region of interest between the two components. We keep this
    # region relatively tight around the line joining the centres so that
    # unrelated distant tracks do not cause spurious connections.
    margin = 25  # pixels on each side of the line between components
    roi_x1 = max(0, min(x1, x2) - margin)
    roi_y1 = max(0, min(y1, y2) - margin)
    roi_x2 = min(binary_image.shape[1], max(x1, x2) + margin)
    roi_y2 = min(binary_image.shape[0], max(y1, y2) + margin)
    
    # Extract region
    roi = binary_image[roi_y1:roi_y2, roi_x1:roi_x2]
    
    if roi.size == 0:
        return False
    
    # Calculate percentage of white pixels (tracks) in ROI
    white_pixels = np.sum(roi > 127)
    total_pixels = roi.size
    track_percentage = white_pixels / total_pixels
    
    # If a significant portion of the ROI is tracks, consider it connected.
    # The original threshold (10%) was far too low and yielded almost-fully
    # connected graphs. We require a stronger signal here.
    threshold = 0.40
    is_connected = track_percentage > threshold
    
    return is_connected


def draw_schematic(graph: CircuitGraph, output_path: str) -> str:
    """
    Draw a schematic diagram using Schemdraw.
    
    Creates a visual representation of the circuit graph with components
    and connections.
    
    Args:
        graph (CircuitGraph): Circuit graph to draw
        output_path (str): Path to save the schematic image
        
    Returns:
        str: Path to the saved schematic image
    """
    try:
        logger.info("Starting schematic drawing...")
        
        with schemdraw.Drawing(show=False) as d:
            d.config(fontsize=12, font='sans-serif')
            
            # Component positioning (simple left-to-right layout)
            components_drawn = {}
            x_pos = 0
            y_pos = 0
            spacing = 3
            
            # Draw components
            for comp in graph.components:
                comp_id = comp['id']
                comp_type = comp['type'].lower()
                
                # Map component types to Schemdraw elements
                if 'resistor' in comp_type:
                    element = elm.Resistor().right().label(comp_id)
                elif 'capacitor' in comp_type:
                    element = elm.Capacitor().right().label(comp_id)
                elif 'ic' in comp_type or 'chip' in comp_type:
                    element = elm.Ic(pins=[elm.IcPin(name='1'), 
                                          elm.IcPin(name='2', side='right')]).label(comp_id)
                elif 'diode' in comp_type:
                    element = elm.Diode().right().label(comp_id)
                elif 'led' in comp_type:
                    element = elm.LED().right().label(comp_id)
                elif 'transistor' in comp_type:
                    element = elm.BjtNpn().label(comp_id)
                else:
                    # Generic element for unknown types
                    element = elm.Resistor().right().label(comp_id)
                
                components_drawn[comp_id] = d.add(element)
                x_pos += spacing
                
                # Wrap to next row after 5 components
                if len(components_drawn) % 5 == 0:
                    x_pos = 0
                    y_pos -= spacing
            
            # Draw connections (simplified - just show as wires)
            for connection in graph.connections:
                parts = connection.split(' -- ')
                if len(parts) == 2:
                    comp1_id, comp2_id = parts
                    # Note: Advanced connection routing would require more complex logic
                    # This is a simplified version showing connectivity
            
        # Save the schematic
        d.save(output_path, dpi=150)
        logger.info(f"Schematic saved to {output_path}")
        
        return output_path
        
    except Exception as e:
        logger.error(f"Error during schematic drawing: {str(e)}")
        # Fallback: create a simple matplotlib visualization
        return draw_simple_graph_visualization(graph, output_path)


def draw_simple_graph_visualization(graph: CircuitGraph, output_path: str) -> str:
    """
    Draw a simple graph visualization using NetworkX and Matplotlib.
    
    Fallback method if Schemdraw drawing fails.
    
    Args:
        graph (CircuitGraph): Circuit graph
        output_path (str): Output file path
        
    Returns:
        str: Path to saved visualization
    """
    logger.info("Drawing simple graph visualization...")
    
    plt.figure(figsize=(12, 8))
    
    # Use spring layout for automatic positioning
    pos = nx.spring_layout(graph.graph, k=2, iterations=50)
    
    # Draw nodes
    nx.draw_networkx_nodes(graph.graph, pos, node_color='lightblue', 
                          node_size=1500, alpha=0.9)
    
    # Draw edges
    nx.draw_networkx_edges(graph.graph, pos, width=2, alpha=0.6)
    
    # Draw labels
    labels = {node: node for node in graph.graph.nodes()}
    nx.draw_networkx_labels(graph.graph, pos, labels, font_size=10, 
                           font_weight='bold')
    
    plt.title("PCB Circuit Schematic", fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    
    # Save figure
    plt.savefig(output_path, dpi=150, bbox_inches='tight', 
               facecolor='white', edgecolor='none')
    plt.close()
    
    logger.info(f"Simple graph visualization saved to {output_path}")
    
    return output_path


def generate_netlist_report(graph: CircuitGraph, output_path: str):
    """
    Generate a text file with the netlist report.
    
    Args:
        graph (CircuitGraph): Circuit graph
        output_path (str): Path to save netlist text file
    """
    with open(output_path, 'w') as f:
        f.write("=" * 50 + "\n")
        f.write("PCB REVERSE ENGINEERING - NETLIST REPORT\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("COMPONENTS:\n")
        f.write("-" * 50 + "\n")
        for comp in graph.components:
            f.write(f"{comp['id']:<10} | {comp['type']:<20}\n")
        
        f.write("\n")
        f.write("CONNECTIONS (Netlist):\n")
        f.write("-" * 50 + "\n")
        for connection in graph.connections:
            f.write(f"{connection}\n")
        
        f.write("\n")
        f.write(f"Total Components: {len(graph.components)}\n")
        f.write(f"Total Connections: {len(graph.connections)}\n")
    
    logger.info(f"Netlist report saved to {output_path}")

