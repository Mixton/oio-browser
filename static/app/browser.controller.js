var app = angular.module("oioBrowser");

app.controller("browserController", ['$scope', 'apiRequest', 'FileUploader', getController]);


function getController($scope, apiRequest, FileUploader) {
  $scope.objects = [];
  $scope.allObjects = [];
  $scope.containers = [];
  $scope.containerInfo = {};
  $scope.currentCont = "";
  $scope.searchedObject = {"s": ""};
  $scope.ccontainer = {"c": ""};
  $scope.uploader = new FileUploader({"autoUpload": true});
  $scope.didSearch = false;
  $scope.created = false;

  $scope.apiRequest = new apiRequest();

  $scope.download = getDownloadUrl;
  $scope.preview = getPreviewUrl;
  $scope.changeCurrentContainer = changeContainer;
  $scope.doSearch = doSearch;
  $scope.createContainer = createContainer;
  $scope.repaginate = repaginate;
  $scope.generatePages = generatePages;

  // Pagination
  const ITEMS_PER_PAGE = 20;

  $scope.currentPage = 1;
  $scope.totalPages = 0;
  $scope.paginatorArray = [];

  (function() {
    $scope.apiRequest.getContainers(function(res) {
      $scope.containers = res.data.containers;
      $scope.currentCont = res.data.containers[0][0];
      $scope.containerInfo = res.data.info || "";

      getObjects($scope.currentCont);
      $scope.uploader.url = '/api/containers/' + $scope.currentCont + '/objects';

      $scope.uploader.onSuccessItem = function(d) {
        getObjects($scope.currentCont);
        $scope.apiRequest.getContainers(function(res) {
            $scope.containers = res.data.containers[0];
            $scope.containerInfo = res.data.info;
      });
      }
    });
  })()

  function getObjects(container) {
    $scope.apiRequest.getObjects(container, function(res) {
      // This array can get very long, so we never bind it as it
      // Instead, we bind to the paginated objects array
      // Also, we don't want to shallow copy the potentially huge array
      // Note: dereferencing via deepcopy can mess up double way binding,
      // so use carefully
      $scope.allObjects = res.data.objects;
      $scope.totalPages = Math.ceil(res.data.objects.length / ITEMS_PER_PAGE)
      $scope.objects = angular.copy(
        $scope.allObjects.slice(
          ($scope.currentPage-1)*ITEMS_PER_PAGE,
          $scope.currentPage*ITEMS_PER_PAGE
        )
      )
      generatePages($scope.currentPages)
    });
  }

  function repaginate(page, relative) {
    if(relative)
      $scope.currentPage += page;
    else
      $scope.currentPage = page

    $scope.objects = angular.copy(
      $scope.allObjects.slice(
        ($scope.currentPage-1)*ITEMS_PER_PAGE,
        $scope.currentPage*ITEMS_PER_PAGE
      )
    )
    generatePages($scope.currentPage)
  }

  function generatePages(currentPage) {
    currentPage = currentPage | 1;
    if($scope.totalPages < 5) {
      var res = Array.from(new Array($scope.totalPages),(val,index)=>index+1);
      $scope.paginatorArray = res
      return
    }
    var res = [1];
    if(currentPage == 1)
      res = [1, 2, '...', $scope.totalPages]
    else if(currentPage == $scope.totalPages)
      res = [1, '...', currentPage - 1, currentPage];
    else
      res = [1, '...', currentPage - 1, currentPage, currentPage + 1, '...', $scope.totalPages]
    $scope.paginatorArray = res
  }

  function createContainer(ccontainer) {
    $scope.apiRequest.createContainer(ccontainer, function(res) {
      $scope.created = true;
      $scope.currentCont = ccontainer;
      $scope.uploader.url = '/api/containers/' + $scope.currentCont + '/objects';
      getObjects($scope.currentCont);
      $scope.apiRequest.getContainers(function(res) {
        $scope.containers = res.data.containers;
        $scope.containerInfo = res.data.info;
      });
      $scope.ccontainer.c ="";
      $scope.created=false;
    });

  }

  function doSearch(searchedObject) {
    $scope.apiRequest.searchObjects($scope.currentCont, searchedObject, function(res) {
      $scope.allObjects = res.data.objects;
      $scope.totalPages = Math.ceil(res.data.objects.length / ITEMS_PER_PAGE)
      $scope.objects = angular.copy(
        $scope.allObjects.slice(
          ($scope.currentPage-1)*ITEMS_PER_PAGE,
          $scope.currentPage*ITEMS_PER_PAGE
        )
      )
      generatePages($scope.currentPages)
      //$scope.objects = res.data.objects;
      //$scope.didSearch = true;
    });
  }

  function getDownloadUrl(name) {
    return "/api/containers/" + $scope.currentCont + "/objects/" + name + "/download";
  }

  function getPreviewUrl(name) {
    return "/api/containers/" + $scope.currentCont + "/objects/" + name + "/preview";
  }

  function changeContainer(name) {
    $scope.currentCont = name;
    $scope.currentPage = 1;
    $scope.uploader.url = '/api/containers/' + name + '/objects';
    getObjects(name);
  }
}
