import React, { useState, useEffect } from "react";
import { useCustomContext } from '../context/TestContext';


const ImageComponent = ({ currentItem }) => {
  const [isImageLarge, setIsImageLarge] = useState(false);
  const [containerHeight, setContainerHeight] = useState("560px"); // Default height
  const { DefaultImge, media_path } = useCustomContext();

  useEffect(() => {
    // Function to set container height based on viewport height
    const updateContainerHeight = () => {
      const viewportHeight = window.innerHeight;
      if (viewportHeight < 800) {
        setContainerHeight("430px");
      } else if (viewportHeight < 890) {
        setContainerHeight("500px");
      } else {
        setContainerHeight("560px");
      }
    };

    // Update container height on component mount and window resize
    updateContainerHeight();
    window.addEventListener("resize", updateContainerHeight);

    // Cleanup on component unmount
    return () => {
      window.removeEventListener("resize", updateContainerHeight);
    };
  }, []);

  useEffect(() => {
    const img = new Image();
    const imgSrc = currentItem.image ? media_path + currentItem.image : DefaultImge;
    
    img.src = currentItem.image ? media_path + currentItem.image : DefaultImge;
    
    
    img.onload = () => {

      
      if (
        img.width > 500 ||
        img.height > 500 ||
        img.height > parseInt(containerHeight) ||
        img.width > parseInt(containerHeight)
      ) {
        // If any condition is met, the image is large
        
        setIsImageLarge(true);
      } else {
        setIsImageLarge(false);
      }
    };
  }, [currentItem]);

  return (
    <div
      className="md:w-[60%] w-full flex items-center justify-center bg-white"
      style={{
        maxHeight: containerHeight,
        minHeight: containerHeight,
        boxShadow: "0 0 10px rgba(0, 0, 0, 0.1)",
      }}
    >
      <img
        src={currentItem.image ? media_path + currentItem.image : DefaultImge}
        alt={currentItem.image}
        className={`${isImageLarge ? "object-fill" : "object-none"} w-full ${currentItem.image.height > 500 ? "h-full" : ""}`}
        style={{
          maxWidth: "100%",
          maxHeight: "100%",                                                                                                                                                                                                                                                                                                                                                                                 
        }}
      />
    </div>
  );
};

export default ImageComponent;
