import { Outlet } from "react-router-dom";
import Variants from "../components/Variants";
import Navbar from "../components/Navbar";
import { useCustomContext } from "../context/TestContext";

function Variantss() {
  const { Background } = useCustomContext();
  return (
    <div
      style={{
        backgroundImage: `url(${Background})`,
        backgroundSize: "cover", // Ensures the image covers the entire container
        backgroundPosition: "center",
        backgroundRepeat: "no-repeat", // Prevents the image from repeating
        backgroundAttachment: "fixed", // Keeps the background image fixed when scrolling
        margin: 0, // Remove default margin
        padding: 0, // Remove default padding
      }}
      >
      <Navbar />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",

        }}
      >
        <Variants />
        <Outlet />
      </div>
    </div>
  );
}

export default Variantss;
