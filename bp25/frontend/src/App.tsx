import React, { useState, useEffect, useRef } from 'react';
import { ChakraProvider, Box, Input, Button, Heading, Text, VStack, Container, Spinner, Flex } from '@chakra-ui/react';
import { defaultSystem } from "@chakra-ui/react";
import { MapContainer, TileLayer, Marker, Popup, Rectangle, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import './App.css';

L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Backend API URL
const API_BASE_URL = 'http://localhost:5000';

// Fixed bounding box size (in percentage of the map view)
const FIXED_BOX_SIZE_PERCENT = 60;

// Component to handle the fixed bounding box
function FixedBoundingBox({ onBoundsChange }: { onBoundsChange: (bounds: [[number, number], [number, number]]) => void }) {
  const map = useMap();
  const [bounds, setBounds] = useState<[[number, number], [number, number]] | null>(null);
  
  // Update bounds when map moves
  useMapEvents({
    moveend: () => {
      updateBounds();
    },
    zoomend: () => {
      updateBounds();
    },
    resize: () => {
      updateBounds();
    }
  });
  
  // Calculate the fixed bounding box in the center of the map
  const updateBounds = () => {
    const center = map.getCenter();
    const bounds = map.getBounds();
    const northEast = bounds.getNorthEast();
    const southWest = bounds.getSouthWest();
    
    // Calculate width and height of the current view
    const latDiff = northEast.lat - southWest.lat;
    const lngDiff = northEast.lng - southWest.lng;
    
    // Use the smaller dimension to ensure a square
    const boxSize = Math.min(
      latDiff * (FIXED_BOX_SIZE_PERCENT / 100),
      lngDiff * (FIXED_BOX_SIZE_PERCENT / 100)
    );
    
    // Calculate the fixed box corners
    const fixedBounds: [[number, number], [number, number]] = [
      [center.lat - boxSize/2, center.lng - boxSize/2],
      [center.lat + boxSize/2, center.lng + boxSize/2]
    ];
    
    setBounds(fixedBounds);
    onBoundsChange(fixedBounds);
  };
  
  // Initialize bounds on first render
  useEffect(() => {
    if (map) {
      updateBounds();
    }
  }, [map]);
  
  return bounds ? (
    <Rectangle 
      bounds={bounds}
      pathOptions={{ color: 'red', weight: 2, fillOpacity: 0.1 }}
    />
  ) : null;
}

function GraphVisualization({ graphData }: { graphData: any }) {
  const map = useMap();
  const legendControlRef = useRef<L.Control | null>(null);
  
  useEffect(() => {
    if (!graphData || !graphData.nodes || !graphData.edges) return;
    
    // Clear previous layers if any
    map.eachLayer((layer) => {
      if (layer instanceof L.Polyline || (layer instanceof L.CircleMarker)) {
        map.removeLayer(layer);
      }
    });
    
    // Remove previous legend control if it exists
    if (legendControlRef.current) {
      map.removeControl(legendControlRef.current);
      legendControlRef.current = null;
    }
    
    // Add nodes
    const nodeMarkers: {[key: string]: L.CircleMarker} = {};
    graphData.nodes.forEach((node: any) => {
      // Determine node color based on route assignment
      let color;
      if (node.route_color) {
        // Use the route color if node is part of a route
        color = node.route_color;
      } else {
        // Otherwise use default colors based on node type
        color = node.type === 'building' ? 'blue' : 
                node.type === 'projection' ? 'green' : '#333';
      }
      
      const radius = node.type === 'building' ? 4 : 
                    node.type === 'projection' ? 2.5 : 3;
      
      const weight = node.type === 'street' ? 1.5 : 1;
      
      const marker = L.circleMarker([node.lat, node.lng], {
        radius: radius,
        fillColor: color,
        color: color,
        weight: weight,
        opacity: 0.9,
        fillOpacity: 0.8
      }).addTo(map);
      
      // Add popup with node information
      if (node.route_id) {
        marker.bindPopup(`Node: ${node.id}<br>Type: ${node.type}<br>Route: ${node.route_id}`);
      } else {
        marker.bindPopup(`Node: ${node.id}<br>Type: ${node.type}`);
      }
      
      nodeMarkers[node.id] = marker;
    });
    
    // Add edges
    graphData.edges.forEach((edge: any) => {
      const sourceNode = graphData.nodes.find((n: any) => n.id === edge.source);
      const targetNode = graphData.nodes.find((n: any) => n.id === edge.target);
      
      if (sourceNode && targetNode) {
        // Determine edge color
        let color;
        if (edge.route_color) {
          // Use route color if edge is part of a route
          color = edge.route_color;
        } else {
          // Otherwise use default colors
          color = edge.type === 'perpendicular' ? '#800080' : '#444';
        }
        
        const weight = edge.type === 'perpendicular' ? 2 : 1.5;
        
        L.polyline([[sourceNode.lat, sourceNode.lng], [targetNode.lat, targetNode.lng]], {
          color: color,
          weight: weight,
          opacity: 0.85
        }).addTo(map);
      }
    });
    
    // Add route information to the legend if routes exist
    if (graphData.routes && graphData.routes.length > 0) {
      // Create a legend control if it doesn't exist
      const legendControl = new L.Control({ position: 'bottomright' });
      
      legendControl.onAdd = function() {
        const div = L.DomUtil.create('div', 'info legend');
        div.style.backgroundColor = 'white';
        div.style.padding = '10px';
        div.style.borderRadius = '5px';
        div.style.boxShadow = '0 0 15px rgba(0,0,0,0.2)';
        
        div.innerHTML = '<h4 style="margin:0 0 5px 0">Legend</h4>';
        
        // Add node type legend
        div.innerHTML += '<div style="margin-bottom:5px;"><strong>Node Types:</strong></div>';
        div.innerHTML += '<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:blue;margin-right:5px;"></span>Building</div>';
        div.innerHTML += '<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:green;margin-right:5px;"></span>Projection</div>';
        div.innerHTML += '<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#333;margin-right:5px;"></span>Street</div>';
        
        // Add edge type legend
        div.innerHTML += '<div style="margin:5px 0;"><strong>Edge Types:</strong></div>';
        div.innerHTML += '<div><span style="display:inline-block;width:12px;height:2px;background:#800080;margin-right:5px;"></span>Building-to-street</div>';
        div.innerHTML += '<div><span style="display:inline-block;width:12px;height:2px;background:#444;margin-right:5px;"></span>Street network</div>';
        
        // Add route legend
        if (graphData.routes && graphData.routes.length > 0) {
          div.innerHTML += '<div style="margin:5px 0;"><strong>Routes:</strong></div>';
          graphData.routes.forEach((route: any) => {
            div.innerHTML += `<div><span style="display:inline-block;width:12px;height:12px;background:${route.color};margin-right:5px;"></span>Route ${route.display_id} (${route.length} nodes)</div>`;
          });
        }
        
        // Add fire station to legend
        if (graphData.fire_stations && graphData.fire_stations.length > 0) {
          div.innerHTML += '<div style="margin:5px 0;"><strong>Facilities:</strong></div>';
          div.innerHTML += '<div><span style="display:inline-block;width:12px;height:12px;background:red;margin-right:5px;"></span>Fire Station</div>';
        }
        
        return div;
      };
      
      legendControl.addTo(map);
      legendControlRef.current = legendControl;
    }
    
    // Cleanup function to remove the legend when component unmounts
    return () => {
      if (legendControlRef.current) {
        map.removeControl(legendControlRef.current);
      }
    };
    
  }, [map, graphData]);
  
  return null;
}

// Add a new component for fire station markers
function FireStationMarkers({ stations }: { stations: any[] }) {
  const fireIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });

  return (
    <>
      {stations.map(station => (
        <Marker 
          key={station.id} 
          position={[station.lat, station.lng]} 
          icon={fireIcon}
        >
          <Popup>
            <div>
              <strong>{station.name}</strong>
              <div>Fire Station</div>
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}

function App() {
  const [location, setLocation] = useState('');
  const [mapLocation, setMapLocation] = useState<[number, number] | null>(null);
  const [locationName, setLocationName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [boundingBox, setBoundingBox] = useState<[[number, number], [number, number]] | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingError, setProcessingError] = useState('');
  const [allocationResult, setAllocationResult] = useState<any>(null);

  const handleSearch = async () => {
    if (!location.trim()) {
      setError('Please enter a location');
      return;
    }
    
    setIsLoading(true);
    setError('');
    setAllocationResult(null);
    
    try {
      // Using OpenStreetMap's Nominatim API for geocoding
      const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(location)}`);
      const data = await response.json();
      
      if (data && data.length > 0) {
        const { lat, lon, display_name } = data[0];
        const parsedLat = parseFloat(lat);
        const parsedLon = parseFloat(lon);
        
        setMapLocation([parsedLat, parsedLon]);
        setLocationName(display_name);
      } else {
        setError('Location not found. Please try a different search term.');
        setMapLocation(null);
      }
    } catch (err) {
      setError('Error searching for location. Please try again.');
      console.error('Geocoding error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const processAllocation = async () => {
    if (!boundingBox) {
      setProcessingError('No area selected for processing');
      return;
    }

    setIsProcessing(true);
    setProcessingError('');
    
    try {
      // Extract coordinates in the format expected by the backend
      const [[south, west], [north, east]] = boundingBox;
      
      // Call backend API to process allocation
      const response = await fetch(`${API_BASE_URL}/api/process-allocation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          bbox: [north, south, east, west],
          location_name: locationName
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Server responded with status: ${response.status}`);
      }
      
      const result = await response.json();
      setAllocationResult(result);
    } catch (err) {
      console.error('Allocation processing error:', err);
      setProcessingError(err instanceof Error ? err.message : "Unknown error occurred");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <ChakraProvider value={defaultSystem}>
      <Box className="app-background" minHeight="100vh" py={8}>
        <Container maxW="container.md">
          <VStack align="center" mb={8}>
            <Heading as="h1" size="2xl" color="teal.600">
              Dispatch Services
            </Heading>
            <Text fontSize="lg" color="gray.600" textAlign="center">
              Intelligent allocation of emergency services during natural disasters.
            </Text>
          </VStack>
          
          <Box 
            bg="white" 
            p={8} 
            borderRadius="lg" 
            boxShadow="lg"
            width="100%" 
            maxWidth="500px" 
            mx="auto"
            mb={6}
          >
            <VStack>
              <Input
                placeholder="Enter location (e.g., Los Angeles, CA)"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                size="lg"
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button 
                onClick={handleSearch} 
                colorScheme="teal" 
                width="100%"
                size="lg"
                _hover={{ bg: "teal.500" }}
                loading={isLoading}
              >
                Search
              </Button>
              {error && <Text color="red.500">{error}</Text>}
            </VStack>
          </Box>
          
          {isLoading && (
            <Box textAlign="center" mt={8}>
              <Spinner size="xl" color="teal.500" />
              <Text mt={2}>Searching for location...</Text>
            </Box>
          )}
          
          {mapLocation && (
            <>
              <Box 
                width="100%" 
                height="600px" 
                borderRadius="lg" 
                overflow="hidden" 
                boxShadow="lg" 
                mt={6}
                mb={4}
                position="relative"
              >
                <Text 
                  position="absolute" 
                  top="10px" 
                  left="50%" 
                  transform="translateX(-50%)" 
                  bg="rgba(255,255,255,0.8)" 
                  px={3} 
                  py={1} 
                  borderRadius="md" 
                  zIndex={1000}
                  fontSize="sm"
                >
                  Move the map to position the red box over your target area
                </Text>
                <MapContainer 
                  center={mapLocation} 
                  zoom={13} 
                  style={{ height: '100%', width: '100%' }}
                  zoomDelta={0.25}
                  zoomSnap={0.25}
                  wheelPxPerZoomLevel={100}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <Marker position={mapLocation}>
                    <Popup>
                      <Text fontWeight="bold">{locationName}</Text>
                    </Popup>
                  </Marker>
                  <FixedBoundingBox onBoundsChange={setBoundingBox} />
                  {allocationResult && allocationResult.graph_data && (
                    <GraphVisualization graphData={allocationResult.graph_data} />
                  )}
                  {allocationResult && allocationResult.fire_stations && (
                    <FireStationMarkers stations={allocationResult.fire_stations} />
                  )}
                </MapContainer>
              </Box>
              
              <Button
                onClick={processAllocation}
                colorScheme="blue"
                size="lg"
                width="100%"
                maxWidth="500px"
                mx="auto"
                loading={isProcessing}
                loadingText="Processing"
                display="block"
              >
                Process Relief Allocation
              </Button>
              
              {processingError && (
                <Text color="red.500" textAlign="center" mt={2}>
                  {processingError}
                </Text>
              )}
              
              {isProcessing && (
                <Box textAlign="center" mt={4}>
                  <Text>Calculating optimal resource allocation...</Text>
                </Box>
              )}
              
              {allocationResult && (
                <Box 
                  mt={6} 
                  p={6} 
                  bg="white" 
                  borderRadius="lg" 
                  boxShadow="md"
                >
                  <Heading size="md" mb={4}>Allocation Results</Heading>
                  <Text>
                    The backend has processed the allocation for {locationName}.
                  </Text>
                  <Text mt={2}>
                    Area processed: {allocationResult.bbox[0].toFixed(6)}, {allocationResult.bbox[2].toFixed(6)} to {allocationResult.bbox[1].toFixed(6)}, {allocationResult.bbox[3].toFixed(6)}
                  </Text>
                  <Text mt={2}>
                    Network nodes: {allocationResult.nodes_count}
                  </Text>
                  <Text mt={2}>
                    Network edges: {allocationResult.edges_count}
                  </Text>
                </Box>
              )}
            </>
          )}
        </Container>
      </Box>
    </ChakraProvider>
  );
}

export default App;
