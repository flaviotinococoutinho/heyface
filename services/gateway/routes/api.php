<?php

use App\Animals\UseCases\EnrollAnimal;
use App\Animals\UseCases\RemoveAnimal;
use App\Animals\UseCases\SearchAnimals;
use App\People\UseCases\EnrollPerson;
use App\People\UseCases\GetPerson;
use App\People\UseCases\ListPeople;
use App\People\UseCases\RemovePerson;
use App\People\UseCases\SearchPeople;
use App\Recognition\UseCases\AnalyzeFace;
use App\Recognition\UseCases\CheckReadiness;
use App\Recognition\UseCases\GetCapabilities;
use App\Recognition\UseCases\ListMethods;
use Illuminate\Support\Facades\Route;

Route::get('health/live', fn () => ['status' => 'ok']);
Route::get('openapi.json', fn () => response(
    file_get_contents(resource_path('contracts/openapi.json')), 200, ['Content-Type' => 'application/json']
));
Route::middleware('throttle:api')->group(function (): void {
    Route::get('capabilities', GetCapabilities::class);
    Route::get('health/ready', CheckReadiness::class);
    Route::get('methods', ListMethods::class);
    Route::post('people', EnrollPerson::class);
    Route::get('people', ListPeople::class);
    Route::get('people/{id}', GetPerson::class)->whereUuid('id');
    Route::delete('people/{id}', RemovePerson::class)->whereUuid('id');
    Route::post('search', SearchPeople::class);
    Route::post('faces/analyze', AnalyzeFace::class);
    Route::post('animals', EnrollAnimal::class);
    Route::post('animals/search', SearchAnimals::class);
    Route::delete('animals/{id}', RemoveAnimal::class)->whereUuid('id');
});
