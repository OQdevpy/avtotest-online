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
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundRepeat: "no-repeat",
        backgroundAttachment: "fixed",
        minHeight: "100vh",
        height: "100%",
        margin: 0,
        padding: 0,
        overflow: "auto",
      }}
      >
      <Navbar />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "flex-start",
          paddingTop: "20px",
          paddingBottom: "40px",
          minHeight: "calc(100vh - 64px)",
        }}
      >
        <Variants />
        <Outlet />
      </div>
    </div>
  );
}

export default Variantss;
