# -*- coding: utf-8 -*-
#  Copyright 2014 Dr. Greg M. Bernstein
""" Classes for computing the loopless k-shortest path problem via Yen's method.
    This implementation uses a modified Dijkstra algorithm
    for computing shortest paths to allow its use in diverse route computations.
"""
from ..packages import networkx as nx
import heapq

class YenKShortestPaths(object):
    """
    This is a straight forward implementation of Yen's K shortest loopless
    path algorithm. No attempt has been made to perform any optimizations
    that have been suggested in the literature. Our main goal was to have a
    functioning K-shortest path algorithm. This implementation should work
    for both undirected and directed  graphs. However it has only been tested
    so far against undirected graphs
    Parameters
    ---------
    graph : networkx.Graph
        the graph of interest
    weight : string
        the string used for the link weight (cost) attribute
    cap : string
        the string used for the link capacity attribute
    """

    def __init__(self, graph, weight="weight", cap="capacity"):
        self.wt = weight
        self.cap = cap
        self.g = graph
        self.pathHeap = [] # Use the heapq module functions heappush(pathHeap, item) and heappop(pathHeap, item)
        self.pathList = [] # Contains WeightedPath objects
        self.deletedEdges = set()
        self.deletedNodes = set()
        self.kPath = None
        # Make a copy of the graph tempG that we can manipulate
        if (isinstance(graph, nx.Graph)):
            self.tempG = graph.copy()
        else:
            self.tempG = None
            

    def findFirstShortestPath(self, source, dest):
        """
        Initialize the k-shortest path algorithm and finds the shortest path.
        You can use this function to restart the algorithm at anytime with
        possibly different source and destination values.

        Parameters
        ----------
        source : string
           The beginning node of the path.
        dest : string
            The termination node of the path.

        Returns
        path : WeightPath
            The shortest path or null if the path doesn't exist.
        """
        # Used to initialize or reinitialize the algorithm
        # Computes the shortest path via Dijsktra
        self.kPath = None
        self.pathHeap = []
        self.pathList = []
        self.source = source
        self.dest = dest
        # Compute the shortest path
        #nodeList = nx.dijkstra_path(self.g, source, dest, self.wt)
        alg = ModifiedDijkstra(self.g, self.wt)
        nodeList = alg.getPath(source, dest, as_nodes = True)
        if not nodeList:
            return None
        deletedLinks = set()
        self.kPath = WeightedPath(nodeList, deletedLinks, self.g, wt=self.wt, cap=self.cap)
        self.kPath.dNode = source
        self.pathList.append(self.kPath)
        return self.kPath


    def getNextShortestPath(self):
        """
        Computes successive shortest path.
        Each one will have a length (cost) greater than or equal
        the previously generated algorithm. Returns null if no more paths can be found.

        You **must** first call findFirstShortestPath(source, dest) to initialize the
        algorithm and set the source and destination node.

        Returns
        -------
        path : WeightedPath
            the next shortest path (or the next longer path depending on
            how you want to think about things).
        """
        if (self.kPath == None):
            raise UserWarning("Must call findFirstShortestPath before this method or no path exists")
        # Iterate over all the nodes in kPath from dNode to the node before the destination
        # and add candidate paths to the path heap.
        kNodes = self.kPath.nodeList
        index = kNodes.index(self.kPath.dNode)
        curNode = kNodes[index]
        while (curNode != self.dest): 
            self._removeEdgesNodes(curNode)
            candidate = self._computeCandidatePath(curNode)
            self._restoreGraph()
            if (candidate != None):
                heapq.heappush(self.pathHeap, candidate)
            index = index + 1
            curNode = kNodes[index]
            
        if (len(self.pathHeap) == 0):
            return None
        p = heapq.heappop(self.pathHeap) # after iterations contains next shortest path
        self.pathList.append(p)
        self.kPath = p     # updates the kth path
        return p

    def _removeEdgesNodes(self, curNode):
        """
        Remove all nodes from source to the node before the current node in kPath.
        Delete the edge between curNode and the next node in kPath
        Delete any edges previously deleted in kPath starting at curNode
        add all deleted edges to the deleted edge list.
        """
        # Figure out all edges to be removed first then take them out of the temp graph
        # then remove all the nodes from the temp graph.
        # At the start the temp graph is equal to the initial graph.
        self.deletedEdges = set()
        self.deletedNodes = set()
        kNodes = self.kPath.nodeList
        index = 0
        tempNode = kNodes[index]
        index += 1
        while (tempNode != curNode):
            edges = self.tempG.edges(tempNode)
            if (len(edges) != 0): 
                for edge in edges:
                    self.deletedEdges.add(edge)
                    self.tempG.remove_edge(edge[0], edge[1])
            #
            self.deletedNodes.add(tempNode)
            self.tempG.remove_node(tempNode)
            tempNode = kNodes[index]
            index += 1
        # Also need to remove those old deleted edges that start on curNode
        oldDelEdges = self.kPath.deletedEdges
        if self.g.is_directed():
            outEdges = self.g.out_edges(curNode)
        else:
            outEdges = self.g.edges(curNode)
        #outEdges = self.g.edges(curNode)
        for  e in outEdges:
            if (e in oldDelEdges):
                self.deletedEdges.add(e)
                self.tempG.remove_edge(e[0], e[1])
        
        # Now delete the edge from the curNode to the next in the path
        tempNode = kNodes[index]
        e = (curNode, tempNode)
        self.deletedEdges.add(e)
        self.tempG.remove_edge(curNode, tempNode)

    
    def _computeCandidatePath(self, curNode):
        """
        Compute the shortest path on the modified graph and then
        combines with the portion of kPath from the source up through
        the deviation node
        """
#        DijkstraShortestPath alg = new DijkstraShortestPath(tempG, wt);
#        List<E> ePath = alg.getPath(curNode, dest);
        
        #nodeList = nx.dijkstra_path(self.tempG, curNode, self.dest, self.wt)
        alg = ModifiedDijkstra(self.tempG, self.wt)
        nodeList = alg.getPath(curNode, self.dest, as_nodes = True)
        # Trying this out...
        if nodeList == None:
            return None

        
        # Get first part of the path from kPath
        nodePath = []
        if (curNode in self.kPath.nodeList):
            index = self.kPath.nodeList.index(curNode)
            nodePath = self.kPath.nodeList[0:index]

        nodePath.extend(nodeList)
        wp = WeightedPath(nodePath, self.deletedEdges, self.g, wt=self.wt,
                          cap=self.cap)
        wp.dNode = curNode
        return wp
    
    def _restoreGraph(self):
        """
        Using the internal deleted node and deleted edge containers
        restores the temp graph to match the graph g.
        """
        self.tempG = self.g.copy()
        self.deletedEdges = []
        self.deletedNodes = []
    
    

class WeightedPath(object):
    """ Used internally by the Yen k-shortest path algorithm and returned to
        user as a result.
    Useful members: nodeList, cost, and capacity.

    Parameters
    ----------
    pathNodeList : list
        a list containing the nodes in the path
    deletedEdges : list
        Use internally by the Yen algorithm
    g : networkx.Graph
        the graph
    """
    def __init__(self, pathNodeList, deletedEdges, g, wt='weight',
                 cap='capacity'):
        """
        Constructor
        """
        self.nodeList = pathNodeList
        self.deletedEdges = set(deletedEdges)
        self.g = g
        self.wt = wt
        self.dNode = None   # The deflection node
        self.cost = 0.0
        self.capacity = float("inf")
        #print "WtPath pathNodeList: {}".format(pathNodeList)
        for i in range(len(pathNodeList)-1):
            self.cost = self.cost + g[pathNodeList[i]][pathNodeList[i+1]][wt]
            if not cap == None:
                self.capacity = min(self.capacity,
                                    g[pathNodeList[i]][pathNodeList[i+1]][cap])
            else:
                self.capacity = None
        
    def __cmp__(self, other):
        if other == None:
            return -1
        return cmp(self.cost, other.cost)
    
    def __str__(self):
        return "nodeList: {}, cost: {}, capacity: {}".format(self.nodeList,
                                                    self.cost, self.capacity)





# Copyright 2014 Dr. Greg M. Bernstein
""" A slightly generalized version of the Dijkstra algorithm.
"""


class ModifiedDijkstra(object):
    """
    The Modified Dijkstra algorithm from "Survivable Networks" by Ramesh Bhandari.
    This algorithm works with graphs that can have directed or undirected links.
    In addition, this algorithm can correctly function in some cases of negative
    arc lengths that arise in the disjoint path computations.

    Works with graphs, *g*, in NetworkX format. Specifically Graph and
    DiGraph classes.

    Parameters
    ----------
    g : networkx.Graph
        a networkx graph or directed graph
    wt : string
        sets the link attribute to be used in computing the path length.
    """
    def __init__(self, g, wt="weight"):
        self.dist = {} # A map from nodes to their labels (float)
        self.predecessor = {} # A map from a node to a node
        self.g = g
        self.wt = wt
        edges = g.edges()
        # Set the value for infinite distance in the graph
        self.inf = 0.0
        for e in edges:
            self.inf += abs(g[e[0]][e[1]][wt])
        self.inf += 1.0


    def getPath(self, source, dest, as_nodes=False):
        """
        Computes the shortest path in the graph between the given `source` and `dest`

        Parameters
        ----------
        source, dest : strings
            The source and destination node identifiers (typically strings)
        as_nodes : boolean
            sets the return content of the path

        Returns
        -------
        path : list
            the path as a list of links (default) or as a list of
            nodes by setting the `as_nodes` keyword argument to *True*.
        """
        self.dist = {} # A map from nodes to their labels (float)
        self.predecessor = {} # A map from a node to a node

        # Initialize the distance labels to "infinity"
        vertices = self.g.nodes()
        for vertex in vertices:
            self.dist[vertex] =  self.inf
            self.predecessor[vertex] = source

        # Further set up the distance from the source to itself and
        # to all one hops away.
        self.dist[source] = 0.0
        if self.g.is_directed():
            outEdges = self.g.out_edges([source])
        else:
            outEdges = self.g.edges([source])
        for edge in outEdges:
            self.dist[edge[1]] = self.g[edge[0]][edge[1]][self.wt]

        s = set(vertices)
        s.remove(source)
        currentMin = self._findMinNode(s)
        if currentMin == None:
            return None
        s.remove(currentMin)
        while currentMin != dest and (len(s) != 0) and currentMin != None:
            if self.g.is_directed():
                outEdges = self.g.out_edges([currentMin])
            else:
                outEdges = self.g.edges([currentMin])
            for edge in outEdges:
                opposite = edge[1]
                if self.dist[currentMin] + \
                        self.g[edge[0]][edge[1]][self.wt] < self.dist[opposite]:
                    self.dist[opposite] = self.dist[currentMin] + \
                                          self.g[edge[0]][edge[1]][self.wt]
                    self.predecessor[opposite] = currentMin
                    s.add(opposite)

            currentMin = self._findMinNode(s)
            #print "Current min node {}, s = {}".format(currentMin, s)
            if currentMin == None:
                return None
            s.remove(currentMin)

        # Compute the path as a list of edges
        currentNode = dest
        predNode = self.predecessor.get(dest)
        node_list = [dest]
        done = False
        path = []
        while not done:
            path.append((predNode, currentNode))
            currentNode = predNode
            predNode = self.predecessor[predNode]
            node_list.append(currentNode)
            done = currentNode == source
        node_list.reverse()
        if as_nodes:
            return node_list
        else:
            return path


    def _findMinNode(self, s):
        """
        Finds the vertex with the minimum distance label in the set "s".
        returns the minimum vertex
        """
        minNode = None
        minVal = self.inf
        for vertex in s:
            if self.dist[vertex] < minVal:
                minVal = self.dist[vertex]
                minNode = vertex
        return minNode