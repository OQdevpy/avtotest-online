import React from 'react';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import { useCustomContext } from './context/TestContext';


function App() {
  const { Background } = useCustomContext();
  
  return (
    <div
      style={{
        backgroundImage: `url(${Background})`,
        backgroundSize: 'cover',  // Ensures the image covers the entire container
        backgroundRepeat: 'no-repeat',  // Prevents the image from repeating
        backgroundAttachment: 'fixed',  // Keeps the background image fixed when scrolling
        height: '100vh',  // Ensure the container takes full viewport height
        margin: 0,  // Remove default margin
        padding: 0,  // Remove default padding
        overflow: 'hidden'  // Prevent overflow
      }}
    >
      <Navbar />
      <Home />
    </div>
  );
}

export default App;
