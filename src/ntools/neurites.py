import networkx as nx
import numpy as np
from scipy.spatial import KDTree
from ntools.dbio import read_edges, read_nodes, delete_nodes, add_nodes, add_edges, check_node, uncheck_nodes, change_type
from magicgui import magicgui, widgets
from ntools.image_reader import wrap_image


class Neurites():
    '''
    Neurites class represents neurites with nodes and associated links between them. It integrates KDTree for efficient spatial querying and NetworkX graph for exploring and retrieving based on graph structure. This allows both proximity-based searches and graph-based operations.
    '''
    def __init__(self,db_path,image_path=None):
        if image_path != None:
            self.image = wrap_image(image_path)
        else:
            self.image = None

        nodes = read_nodes(db_path)
        edges = read_edges(db_path)
        
        self.G = nx.Graph() # networkx graph
        for node in nodes:
            self.G.add_node(node['nid'], nid = node['nid'], coord = node['coord'], type = node['type'], checked = node['checked'])

        for edge in edges:
            self.G.add_edge(edge['src'],edge['des'],creator = edge['creator'])

        coords = []
        coord_ids = []
        for node in nodes:
            coords.append(node['coord'])
            coord_ids.append(node['nid'])
        self.kdtree = KDTree(np.array(coords))
        self.coord_ids = coord_ids

    
    def get_pn_links(self,k,dis_thres):
        # augment graph by adding knn edges
        # to be finished
        for node in self.G.nodes:
            coord = self.G.nodes[node]['coord']
            d, nbrs = self.kdtree.query(coord, k, p=2)
            nbrs = [self.coord_ids[i] for i in nbrs]
            print(d,nbrs,sep='\n')
        return
    

    def get_segs_within(self,roi):
        # get segs within roi, return a list of lists of nodes
        # 1. query nodes within roi
        # 2. generate subgraph
        # 3. remove branches, then traverse every connected components
        # 4. filter out short paths
        assert roi[3]==roi[4] and roi[4]==roi[5] # process cubic image block
        c_coord = [i+j//2-1 for i,j in zip(roi[0:3],roi[3:6])]
        nbrs = self.kdtree.query_ball_point(c_coord, roi[3]/2, p=float(np.inf))
        nbrs = [self.coord_ids[i] for i in nbrs]
        sub_g = self.G.subgraph(nbrs).copy()
        branch_nodes = [node for node, degree in sub_g.degree() if degree >= 3]
        sub_g.remove_nodes_from(branch_nodes) 
        connected_components = list(nx.connected_components(sub_g))
        segs = []
        for nodes in connected_components:
            end_nodes = [node for node in nodes if sub_g.degree[node] == 1]
            if (len(end_nodes)!=2):
                continue
            path = nx.shortest_path(sub_g, source=end_nodes[0], target=end_nodes[1], weight=None, method='dijkstra') 
            path = [[i-j for i,j in zip(self.G.nodes[node]['coord'],roi[0:3])] for node in path]
            segs.append(path)
        # get intensity value
        img = self.image.from_roi(roi)
        intens = []
        for seg in segs:
            seg_intens = []
            for coord in seg:
                seg_intens.append(img[coord[0],coord[1],coord[2]])
            intens.append(seg_intens)

        return segs, intens



if __name__ == '__main__':
    db_path = '/Users/bean/workspace/data/RM009_axons_1.db'
    image_path = '/Users/bean/workspace/data/RM009_axons_1.tif'
    neurites = Neurites(db_path,image_path=image_path)
    roi = [0,0,0,300,300,300]
    segs,intens = neurites.get_segs_within(roi)
    print(len(segs),len(intens))
    import napari
    viewer = napari.Viewer(ndisplay=3)
    img = neurites.image.from_roi(roi)
    viewer.add_image(img)
    segs = sum(segs,[])
    viewer.add_points(np.array(segs),size=2)
    napari.run()