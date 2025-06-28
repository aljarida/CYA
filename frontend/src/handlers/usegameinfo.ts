import { useState, useEffect } from "react";

const useGameInfo = () => {
  const [gameInfo, setGameInfo] = useState({
    playerName: "",
    worldTheme: "",
    playerDescription: "",
  });

  const [isFormValid, setIsFormValid] = useState(false);

  useEffect(() => {
    setIsFormValid(
      gameInfo.playerName.trim() !== "" && 
      gameInfo.worldTheme.trim() !== "" &&
	    gameInfo.playerDescription.trim() !== ""
    );
  }, [gameInfo]);

  const handleInputChange = (e: any) => {
    const { name, value } = e.target;
    setGameInfo(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return { gameInfo, isFormValid, handleInputChange };
};

export default useGameInfo;
