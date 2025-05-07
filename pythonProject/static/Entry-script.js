document.addEventListener("DOMContentLoaded", function() {
    const preloader = document.getElementById("preloader");
    const video = document.getElementById("video-player");
    const playButton = document.getElementById("play-button");
    const startVideoBtn = document.getElementById("start-video-btn");
    const readyBtn = document.getElementById("ready-btn");
    const notReadyBtn = document.getElementById("not-ready-btn");

    // Sayfa yüklenince preloader'ı kaldır
    window.addEventListener("load", function() {
        preloader.style.opacity = "0";
        setTimeout(() => preloader.style.display = "none", 500);
    });

    // Videoyu otomatik oynatmayı dene
    video.muted = true;  // Sessiz başlat (Tarayıcı engelini aşmak için)
    video.play().then(() => {
        video.muted = false; // Başladıktan sonra sesi aç
    }).catch(error => {
        console.log("Otomatik oynatma engellendi, kullanıcı etkileşimi gerekli.", error);
        startVideoBtn.style.display = "block"; // Butonu göster
    });

    // Kullanıcı videoya tıklarsa oynatma/durdurma
    video.addEventListener("click", function() {
        if (!video.paused) {
            video.pause();
            playButton.style.display = "block";
        } else {
            video.play();
            playButton.style.display = "none";
        }
    });

    // Eğer tarayıcı otomatik başlatmayı engellerse, butona tıklanınca başlat
    startVideoBtn.addEventListener("click", function() {
        video.muted = false;
        video.play();
        startVideoBtn.style.display = "none"; // Butonu gizle
    });

    // Video oynatılınca butonu ve simgeyi gizle
    video.addEventListener("play", function() {
        playButton.style.display = "none";
        startVideoBtn.style.display = "none";
    });

    // ✅ "Hazırım, Devam" butonuna basınca sohbet sayfasına yönlendir
    readyBtn.addEventListener("click", function() {
        window.location.href = "/chat";
    });

    // "Kendimi Hazır Hissetmiyorum" butonu
    notReadyBtn.addEventListener("click", function() {
        alert("Endişelenme, hazır hissettiğinde tekrar gelebilirsin! 😊");
    });
});