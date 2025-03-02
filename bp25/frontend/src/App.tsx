import React, { useState } from 'react';
import { ChakraProvider, Box, Input, Button, Heading, Text, VStack, Container } from '@chakra-ui/react';
import { defaultSystem } from "@chakra-ui/react"
import './App.css';

function App() {
  const [location, setLocation] = useState('');

  const handleSearch = () => {
    if (!location.trim()) {
      alert('Please enter a location');
      return;
    }
    alert(`Searching for: ${location}`);
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
          >
            <VStack>
              <Input
                placeholder="Enter location (e.g., Los Angeles, CA)"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                size="lg"
              />
              <Button 
                onClick={handleSearch} 
                colorScheme="teal" 
                width="100%"
                size="lg"
                _hover={{ bg: "teal.500" }}
              >
                Search
              </Button>
            </VStack>
          </Box>
        </Container>
      </Box>
    </ChakraProvider>
  );
}

export default App;
