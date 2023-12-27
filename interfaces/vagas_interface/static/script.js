function teste() {
    fetch('http://localhost:8000/vagas/page/1')
    .then((response) => { return response.json() })
    .then((data) => {
        console.log(data) 
    });
}

// function teste2() {
//     fetch('http://localhost:8000/vagas/teste2/')
//     .then((response) => { return response.json() })
//     .then((data) => {
//         console.log(data) 
//     });
// }