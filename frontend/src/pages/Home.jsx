import { Outlet } from "react-router-dom"
import HomePage from "../components/HomePage"
function Home() {
  return (
    <div style={
      {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
      }
    }>
      <HomePage />
      <Outlet />
    </div>
  )
}

export default Home