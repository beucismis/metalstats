document.addEventListener("DOMContentLoaded", function () {
  const authStatusDiv = document.getElementById("auth-status");

  if (authStatusDiv) {
    fetch("/auth-status")
      .then((response) => response.json())
      .then((data) => {
        const canvasGeneratorDiv = document.getElementById("canvas-generator");
        const loginPromptDiv = document.getElementById("login-prompt");

        if (data.logged_in) {
          authStatusDiv.innerHTML = `<a href="/logout">Logout Spotify</a>`;
          if (canvasGeneratorDiv) {
            canvasGeneratorDiv.style.display = "block";
          }
          if (loginPromptDiv) {
            loginPromptDiv.style.display = "none";
          }
        } else {
          authStatusDiv.innerHTML = '<a href="/login">Login with Spotify</a>';
          if (canvasGeneratorDiv) {
            canvasGeneratorDiv.style.display = "none";
          }
          if (loginPromptDiv) {
            loginPromptDiv.style.display = "block";
          }
        }
      });
  }

  const canvasForm = document.getElementById("canvas-form");

  if (canvasForm) {
    canvasForm.addEventListener("submit", function (event) {
      event.preventDefault();
      const form = event.target;
      const type = form.type.value;
      const time_range = form.time_range.value;
      const limit = form.limit.value;
      const canvasContainer = document.getElementById("canvas-container");
      canvasContainer.innerHTML = '<div class="loader"></div>';
      document.getElementById("share-controls").style.display = "none";

      const url = `/top-canvas?type=${type}&time_range=${time_range}&limit=${limit}`;

      console.log("Starting canvas generation fetch for:", url);

      fetch(url)
        .then((response) => {
          console.log("Received response from server. Status:", response.status);
          if (response.ok) {
            console.log("Response is OK, processing blob...");
            return response.blob();
          }
          console.error("Response was not OK.");
          throw new Error("Failed to generate canvas. Please try again.");
        })
        .then((blob) => {
          console.log("Blob received, creating image URL.");
          const imageUrl = URL.createObjectURL(blob);
          canvasContainer.innerHTML = `<img src="${imageUrl}" alt="Top Canvas">`;
          document.getElementById("share-controls").style.display = "block";
          console.log("Canvas generation complete.");
        })
        .catch((error) => {
          console.error("An error occurred during canvas generation:", error);
          canvasContainer.innerHTML = `<p style="color: red;">${error.message}</p>`;
        });
    });
  }

  const shareButton = document.getElementById("share-button");

  if (shareButton) {
    shareButton.addEventListener("click", function () {
      const shareStatus = document.getElementById("share-status");
      const isAnonymous = document.getElementById("anonymous-share").checked;

      const form = document.getElementById("canvas-form");
      const type = form.type.value;
      const time_range = form.time_range.value;
      const limit = form.limit.value;

      shareButton.disabled = true;
      shareStatus.innerHTML = '<div class="loader"></div>';

      fetch("/share-to-showcase", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          type: type,
          time_range: time_range,
          limit: parseInt(limit),
          share_anonymously: isAnonymous,
        }),
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Failed to share. Please try again.");
          }
          return response.json();
        })
        .then((data) => {
          shareStatus.innerHTML = `Shared successfully! View <a href="/showcase">Showcase</a>.`;
          shareButton.disabled = false;
        })
        .catch((error) => {
          shareStatus.textContent = error.message;
          shareButton.disabled = false;
        });
    });
  }

  const showcaseContainer = document.getElementById("showcase-container");

  if (showcaseContainer && window.location.pathname === "/showcase") {
    showcaseContainer.innerHTML = '<div class="loader"></div>';
    fetch("/showcase-items")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load showcase items.");
        }
        return response.json();
      })
      .then((items) => {
        showcaseContainer.innerHTML = "";
        if (items.length === 0) {
          showcaseContainer.innerHTML = "<p>The showcase is empty. Be the first to share a canvas!</p>";
          return;
        }

        items.forEach((item) => {
          const itemDiv = document.createElement("div");
          itemDiv.className = "showcase-item";

          const img = document.createElement("img");
          img.src = `/images/${item.image_filename}`;
          img.alt = `Canvas by ${item.creator_name}`;

          const creatorP = document.createElement("p");
          const creationDate = new Date(item.created_at).toLocaleString(undefined, {
            year: "numeric",
            month: "numeric",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          });

          if (item.creator_spotify_id) {
            const creatorLink = document.createElement("a");
            creatorLink.href = `https://open.spotify.com/user/${item.creator_spotify_id}`;
            creatorLink.textContent = item.creator_name;
            creatorLink.target = "_blank";
            creatorP.innerHTML = `By `;
            creatorP.appendChild(creatorLink);
            creatorP.innerHTML += ` on ${creationDate}`;
          } else {
            creatorP.textContent = `By ${item.creator_name} on ${creationDate}`;
          }

          itemDiv.appendChild(img);
          itemDiv.appendChild(creatorP);
          showcaseContainer.appendChild(itemDiv);
        });
      })
      .catch((error) => {
        showcaseContainer.innerHTML = `<p style="color: red;">${error.message}</p>`;
      });
  }
});
